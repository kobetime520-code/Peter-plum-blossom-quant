"""
git_sync.py — 彼夫有責戰情室自動推送腳本
V1.3 | 2026-08-01
用途：將戰報檔案精準推送至 GitHub main 分支
      ・本地執行 radar.py 時由 radar.py 結尾自動呼叫（預設白名單 5 檔）
      ・mengong_auto.py 每日 21:00 呼叫（指定 mengong_summary.json）
      ・GitHub Actions 環境由 workflow 負責，不重複呼叫
嚴禁：finmind_cache.json / finmind_info_cache.json 等快取檔不在推送清單中
改善：pull --rebase 前自動 stash 殘留變動；JSON 衝突自動以本地掃描結果覆蓋
V1.2 修復：修正 stash 判定 bug — 無本地變動時 git stash 不建立 stash，舊版
      誤以 `git stash list` 非空判定 stashed，導致事後誤 pop 到堆疊中的舊 stash
      （曾使 CLAUDE.md 反覆冒出衝突標記、阻斷排程推送）。改以 stash 前後數量差
      判定，且 pop 時指名本次那顆 stash@{0}。
V1.3 收斂（稽核 D1）：
      ① sync_to_github() 參數化 —— 可指定推送檔案清單與 commit 訊息，
         讓 mengong_auto.py 停用自帶的 git add/commit/push 旁路，
         兩條推送路徑共用同一套 stash／pull／pop／重試邏輯。
      ② 衝突處理的 `checkout --theirs` 目標改為「本次傳入的檔案」，
         不再寫死 SYNC_FILES —— 孟恭推送時不會誤覆寫戰報檔。
      ③ 新增 .git_sync.lock 互斥鎖 —— 孟恭 21:00 的推送落在 radar
         （20:39 起、實測約 45 分鐘）執行區間內，兩者過去靠碰運氣避開，
         現改為明確排隊；陳舊鎖（> 10 分鐘）自動回收，避免死鎖。
"""
import sys
import io

# 強制 UTF-8 輸出，防止 Windows CP950 終端對 emoji 拋 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import subprocess
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta

# 台灣時區 UTC+8
TW_TZ = timezone(timedelta(hours=8))

# 專案根目錄（與 radar.py 同層）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 精準推送清單（只上傳戰報檔案）
# 註：backtest_report.json 每週六由 backtest_run.py 產生；平日無變動時 git 自動略過（nothing to commit）
# 註：mengong_summary.json 不列此處 —— 由 mengong_auto.py 自行以參數傳入，
#     避免 radar 執行期間把孟恭正在寫入的半成品一併提交。
SYNC_FILES = [
    "plum_blossom_data.json",
    "ocean_history.json",
    "log_report.json",
    "backtest_report.json",
    "grace_theme_data.json",
]

# ── 推送互斥鎖（V1.3）────────────────────────────────────────────────
LOCK_FILE = os.path.join(BASE_DIR, ".git_sync.lock")
LOCK_WAIT_SECONDS = 180    # 最多等前一支推送完成
LOCK_POLL_SECONDS = 3
LOCK_STALE_SECONDS = 600   # 超過此秒數視為前次異常終止的殘留鎖


def run_git(args):
    """執行 git 指令，回傳 (success: bool, output: str)"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "⏰ Git 指令逾時（60 秒），可能為網路異常"
    except FileNotFoundError:
        return False, "❌ 找不到 git 指令，請確認 Git 已安裝並加入 PATH"
    except Exception as e:
        return False, f"❌ 未知錯誤：{e}"


@contextmanager
def _repo_lock():
    """
    以 O_CREAT|O_EXCL 建立 .git_sync.lock，確保同一 repo 同時只有一支推送在跑。

    yield True 代表成功取得鎖；yield False 代表等待逾時（呼叫端應放棄推送）。
    鎖檔超過 LOCK_STALE_SECONDS 未釋放視為前次異常終止的殘留，自動回收。
    """
    acquired = False
    waited_notice = False
    deadline = time.time() + LOCK_WAIT_SECONDS

    while True:
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                stamp = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M:%S")
                os.write(fd, f"pid={os.getpid()} at={stamp}\n".encode("utf-8"))
            finally:
                os.close(fd)
            acquired = True
            break
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(LOCK_FILE)
            except OSError:
                continue  # 鎖剛好被釋放，立刻重搶
            if age > LOCK_STALE_SECONDS:
                print(f"  🔓 偵測到陳舊推送鎖（{int(age)} 秒未釋放），判定為殘留並回收")
                try:
                    os.remove(LOCK_FILE)
                except OSError:
                    pass
                continue
            if time.time() >= deadline:
                break
            if not waited_notice:
                print(f"  ⏳ 另一支推送進行中，等待推送鎖（最多 {LOCK_WAIT_SECONDS} 秒）...")
                waited_notice = True
            time.sleep(LOCK_POLL_SECONDS)

    try:
        yield acquired
    finally:
        if acquired:
            try:
                os.remove(LOCK_FILE)
            except OSError:
                pass


def _do_sync(existing, commit_msg):
    """實際推送流程：git add → commit → stash → pull --rebase → pop → push"""
    # ── Step 1：git add（只加存在的戰報檔案）────────────────────────────
    ok, out = run_git(["add"] + existing)
    if not ok:
        print(f"  ❌ git add 失敗：{out}")
        return False
    print(f"  ✅ git add：{', '.join(existing)}")

    # ── Step 2：git commit ───────────────────────────────────────────────
    # ⚠️ 關鍵防呆（V1.3）：先明確判斷「本次檔案有無實際變更」，不要靠 git commit
    # 的錯誤訊息字串。工作區若有其他未暫存變動，git 會回「no changes added to
    # commit」而非「nothing to commit」，舊版字串比對漏接、把無變更誤判為推送失敗。
    # 此前 log_report.json 因 push_status 回寫而恆為 dirty，永遠有東西可提交，
    # 遮蔽了這個瑕疵；E5 讓工作區恢復乾淨後才會踩到。
    no_change, _ = run_git(["diff", "--cached", "--quiet", "--"] + existing)
    if no_change:
        print("  ℹ️  無變更需提交，資料與雲端一致，略過 commit")
        return True  # 不算失敗

    ok, out = run_git(["commit", "-m", commit_msg])
    if not ok:
        if "nothing to commit" in out.lower():
            print("  ℹ️  無變更需提交，資料與雲端一致，略過 commit")
            return True  # 不算失敗
        else:
            print(f"  ❌ git commit 失敗：{out}")
            return False
    print(f"  ✅ git commit：{commit_msg}")

    # ── Step 3：stash 殘留變動，確保工作區乾淨再 pull --rebase ─────────────
    # 注意：不用 --include-untracked，避免 yf_info_cache.json 等快取檔被吃進 stash
    # 導致 pop 時因檔案已被 radar.py 更新而衝突，誤觸 returncode ≠ 0
    #
    # ⚠️ 關鍵防呆（V1.2）：「無本地變動」時 git stash 回傳 0 但不建立 stash，
    # 若只看 `git stash list` 非空就判定 stashed，會誤 pop 到堆疊裡的舊 stash
    # （曾導致 CLAUDE.md 反覆冒出衝突標記）。改以「stash 前後數量差」判斷本次
    # 是否真的建立 stash，且事後只 pop 本次那顆（stash@{0}，剛建立必在頂端）。
    def _stash_count():
        _, lst = run_git(["stash", "list"])
        return len(lst.splitlines()) if lst.strip() else 0

    before_count = _stash_count()
    ok_stash, stash_out = run_git(["stash", "push", "-m", "molysync-auto"])
    stashed = ok_stash and _stash_count() > before_count
    if stashed:
        print(f"  📦 stash：暫存殘留變動，確保 rebase 可執行（{stash_out[:60]}）")

    print("  🔄 執行 git pull --rebase，融合雲端最新變動...")
    ok, out = run_git(["pull", "--rebase", "origin", "main"])

    if not ok:
        if "CONFLICT" in out:
            # JSON 戰報衝突 → 以本地掃描結果為權威來源
            # V1.3：只解本次推送的檔案，不再對整份 SYNC_FILES 動手
            print("  ⚠️ 偵測到 JSON 衝突，以本地掃描結果覆蓋遠端...")
            run_git(["checkout", "--theirs"] + existing)
            run_git(["add"] + existing)
            ok_cont, cont_out = run_git(["rebase", "--continue"])
            # git 2.x 在衝突全由 checkout 解決後，可能回傳非零但附帶成功訊息
            rebase_ok = ok_cont or any(
                kw in cont_out.lower()
                for kw in ["nothing to commit", "successfully rebased", "no changes"]
            )
            if not rebase_ok:
                print(f"  ❌ rebase --continue 失敗：{cont_out}")
                run_git(["rebase", "--abort"])
                if stashed:
                    run_git(["stash", "pop", "stash@{0}"])
                return False
            print("  ✅ 衝突已解除，本地掃描結果已保留")
        else:
            print(f"  ⚠️ git pull --rebase 失敗：{out}")
            if stashed:
                run_git(["stash", "pop", "stash@{0}"])
            return False
    else:
        print("  ✅ git pull --rebase 完成")

    if stashed:
        run_git(["stash", "pop", "stash@{0}"])
        print("  📦 stash pop：殘留變動已還原")

    # ── Step 4：git push（最多重試 2 次，間隔 15 秒）────────────────────
    for attempt in range(1, 3):
        ok, out = run_git(["push", "origin", "main"])
        if ok:
            print(f"  ✅ git push：成功推送至 GitHub main ✨（第 {attempt} 次）")
            return True
        print(f"  ⚠️ git push 第 {attempt} 次失敗：{out}")
        if attempt < 2:
            print("     15 秒後重試...")
            time.sleep(15)
    print("     建議手動執行：git pull --rebase && git push origin main")
    return False


def sync_to_github(files=None, commit_msg=None):
    """
    主流程：取得推送鎖 → git add → git commit → git push
    任何步驟失敗皆印出警告，不讓整個系統崩潰。

    files      ：要推送的檔案清單（相對本目錄）。None 表示使用預設戰報白名單。
    commit_msg ：commit 訊息。None 表示使用 Moly 每日戰報的預設訊息。
    """
    files = list(files) if files else list(SYNC_FILES)
    if commit_msg is None:
        taiwan_time = datetime.now(TW_TZ)
        commit_msg = f"🤖 自動更新：Moly Daily Report {taiwan_time.strftime('%Y-%m-%d %H:%M')}"

    print("\n🔗 git_sync.py 啟動：準備推送至 GitHub main...")

    existing = [f for f in files if os.path.exists(os.path.join(BASE_DIR, f))]
    if not existing:
        print("  ⚠️ 找不到任何待推送檔案，跳過推送")
        return False

    with _repo_lock() as acquired:
        if not acquired:
            print(f"  ❌ 等待推送鎖逾時（{LOCK_WAIT_SECONDS} 秒），本次略過推送")
            print("     另一支推送可能仍在進行，請稍後手動執行：python git_sync.py")
            return False
        return _do_sync(existing, commit_msg)


if __name__ == "__main__":
    # 不帶參數 = 預設戰報白名單；帶參數 = 只推送指定檔案
    cli_files = sys.argv[1:] or None
    success = sync_to_github(files=cli_files)
    sys.exit(0 if success else 1)
