"""
git_sync.py — 彼夫有責戰情室自動推送腳本
V1.1 | 2026-05-12
用途：將三大戰報檔案精準推送至 GitHub main 分支
      ・本地執行 radar.py 時由 radar.py 結尾自動呼叫
      ・GitHub Actions 環境由 auto_radar.yml 負責，不重複呼叫
嚴禁：finmind_cache.json / finmind_info_cache.json 等快取檔不在推送清單中
改善：pull --rebase 前自動 stash 殘留變動；JSON 衝突自動以本地掃描結果覆蓋
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
from datetime import datetime, timezone, timedelta

# 台灣時區 UTC+8
TW_TZ = timezone(timedelta(hours=8))

# 專案根目錄（與 radar.py 同層）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 精準推送清單（只上傳這三個戰報檔案）
SYNC_FILES = [
    "plum_blossom_data.json",
    "ocean_history.json",
    "log_report.json",
]


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


def sync_to_github():
    """
    主流程：git add → git commit → git push
    任何步驟失敗皆印出警告，不讓整個系統崩潰。
    """
    taiwan_time = datetime.now(TW_TZ)
    commit_msg = f"🤖 自動更新：Moly Daily Report {taiwan_time.strftime('%Y-%m-%d %H:%M')}"

    print("\n🔗 git_sync.py 啟動：準備推送戰報至 GitHub main...")

    # ── Step 1：git add（只加存在的戰報檔案）────────────────────────────
    existing = [f for f in SYNC_FILES if os.path.exists(os.path.join(BASE_DIR, f))]
    if not existing:
        print("  ⚠️ 找不到任何戰報檔案，跳過推送")
        return False

    ok, out = run_git(["add"] + existing)
    if not ok:
        print(f"  ❌ git add 失敗：{out}")
        return False
    print(f"  ✅ git add：{', '.join(existing)}")

    # ── Step 2：git commit ───────────────────────────────────────────────
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
    ok_stash, stash_out = run_git(["stash", "--include-untracked"])
    stashed = ok_stash and "Saved working directory" in stash_out
    if stashed:
        print("  📦 stash：暫存殘留變動，確保 rebase 可執行")

    print("  🔄 執行 git pull --rebase，融合雲端最新變動...")
    ok, out = run_git(["pull", "--rebase", "origin", "main"])

    if not ok:
        if "CONFLICT" in out:
            # JSON 戰報衝突 → 以本地 Moly 掃描結果為權威來源
            print("  ⚠️ 偵測到 JSON 衝突，以本地掃描結果覆蓋遠端...")
            conflicted = [f for f in SYNC_FILES if os.path.exists(os.path.join(BASE_DIR, f))]
            run_git(["checkout", "--theirs"] + conflicted)
            run_git(["add"] + conflicted)
            ok_cont, cont_out = run_git(["rebase", "--continue"],)
            if not ok_cont and "nothing to commit" not in cont_out.lower():
                print(f"  ❌ rebase --continue 失敗：{cont_out}")
                run_git(["rebase", "--abort"])
                if stashed:
                    run_git(["stash", "pop"])
                return False
            print("  ✅ 衝突已解除，本地掃描結果已保留")
        else:
            print(f"  ⚠️ git pull --rebase 失敗：{out}")
            if stashed:
                run_git(["stash", "pop"])
            return False
    else:
        print("  ✅ git pull --rebase 完成")

    if stashed:
        run_git(["stash", "pop"])
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
            import time as _time
            _time.sleep(15)
    print("     建議手動執行：git pull --rebase && git push origin main")
    return False


if __name__ == "__main__":
    success = sync_to_github()
    sys.exit(0 if success else 1)
