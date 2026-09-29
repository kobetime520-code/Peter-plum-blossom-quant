"""
tests/test_git_sync.py — git_sync 推送流程離線回歸測試（2026-09-29 推送失敗事件）

性質：純離線。以暫存目錄建立「本機 bare repo 當 origin ＋ 工作 clone」，
      全程不碰 GitHub、不動專案 repo、不讀寫真實戰報檔。
執行：python tests/run_all.py     （或 python tests/test_git_sync.py）

重現的事件：2026-09-29 21:17 兩次 git push 皆遭 GitHub 回 500，戰報 commit 滯留本機；
依告警執行 `python git_sync.py` 補推，卻因「無新變更」直接回報成功、實際未推。
本測試以 pre-receive hook 拒收模擬 GitHub 5xx。

涵蓋範圍：
  ① 滯留 commit ＋ 無新變更 → 仍須推出（V1.3 的 bug，V1.4 修正）
  ② 無滯留 ＋ 無新變更 → 略過推送、不產生 commit（不誤推）
  ③ 有新變更 → commit 並推送（既有行為回歸）
  ④ 遠端短暫拒收 2 次 → 退避重試後成功
  ⑤ 重試全數失敗 → 回報失敗、commit 留在本機；遠端恢復後下一次無變更的同步自動帶走（自癒）
  ⑥ 逾時預算：持鎖最壞時間 < 陳舊鎖門檻；radar 子程序逾時 ≥ 等鎖 ＋ 持鎖最壞時間
"""
import sys
import os
import shutil
import subprocess
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import git_sync
import radar

_checks = 0

# pre-receive hook：前 N 次拒收（模擬 GitHub 500），之後放行。N 由 bare repo 內的 fail_budget 檔決定。
_HOOK = """#!/bin/sh
n=$(cat fail_budget 2>/dev/null || echo 0)
if [ "$n" -gt 0 ]; then
  echo $((n-1)) > fail_budget
  echo "remote: Internal Server Error (simulated)" >&2
  exit 1
fi
exit 0
"""


def ok(cond, msg):
    global _checks
    _checks += 1
    if not cond:
        raise AssertionError(msg)
    print(f"  ✅ {msg}")


def section(title):
    print(f"\n── {title} " + "─" * max(0, 56 - len(title)))


def _git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout.strip() or r.stderr.strip())


class _Sandbox:
    """bare origin ＋ 工作 clone，並把 git_sync 的工作目錄與鎖檔導向 clone。"""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="gitsync_test_")
        self.origin = os.path.join(self.root, "origin.git")
        self.work = os.path.join(self.root, "work")
        _git(self.root, "init", "--bare", "-b", "main", self.origin)
        _git(self.root, "clone", self.origin, self.work)
        for k, v in (("user.name", "test"), ("user.email", "test@example.com"),
                     ("core.autocrlf", "false"), ("commit.gpgsign", "false")):
            _git(self.work, "config", k, v)
        self.write("data.json", '{"v": 0}\n')
        _git(self.work, "add", "data.json")
        _git(self.work, "commit", "-m", "init")
        _git(self.work, "push", "origin", "main")
        hook = os.path.join(self.origin, "hooks", "pre-receive")
        with open(hook, "w", encoding="utf-8", newline="\n") as f:
            f.write(_HOOK)
        os.chmod(hook, 0o755)

        self._saved = (git_sync.BASE_DIR, git_sync.LOCK_FILE, git_sync.PUSH_RETRY_DELAYS)
        git_sync.BASE_DIR = self.work
        git_sync.LOCK_FILE = os.path.join(self.work, ".git_sync.lock")
        git_sync.PUSH_RETRY_DELAYS = (0, 0, 0)   # 次數不變、免等待

    def write(self, name, text):
        with open(os.path.join(self.work, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def fail_next(self, n):
        with open(os.path.join(self.origin, "fail_budget"), "w", encoding="utf-8", newline="\n") as f:
            f.write(f"{n}\n")

    def remote_head(self):
        return _git(self.origin, "rev-parse", "main")[1]

    def local_head(self):
        return _git(self.work, "rev-parse", "HEAD")[1]

    def ahead(self):
        return int(_git(self.work, "rev-list", "--count", "origin/main..HEAD")[1])

    def commit_count(self):
        return int(_git(self.work, "rev-list", "--count", "HEAD")[1])

    def sync(self):
        return git_sync.sync_to_github(files=["data.json"], commit_msg="auto")

    def close(self):
        git_sync.BASE_DIR, git_sync.LOCK_FILE, git_sync.PUSH_RETRY_DELAYS = self._saved
        shutil.rmtree(self.root, ignore_errors=True)


def _run(fn):
    sb = _Sandbox()
    try:
        fn(sb)
    finally:
        sb.close()


# =====================================================================
def test_stranded_commit_pushed():
    section("① 滯留 commit ＋ 無新變更 → 仍須推出（09-29 事件）")

    def body(sb):
        sb.write("data.json", '{"v": 1}\n')
        sb.fail_next(99)                              # 遠端持續 500
        ok(sb.sync() is False, "遠端持續拒收 → 回報失敗")
        ok(sb.ahead() == 1, "失敗後戰報 commit 滯留本機（領先 origin 1 筆）")

        sb.fail_next(0)                               # 遠端恢復
        before = sb.commit_count()
        ok(sb.sync() is True, "無新變更時執行補推 → 回報成功")
        ok(sb.ahead() == 0, "滯留 commit 已推出（V1.3 此處仍領先 1 筆）")
        ok(sb.remote_head() == sb.local_head(), "遠端 main 與本機 HEAD 一致")
        ok(sb.commit_count() == before, "補推未額外產生空 commit")
    _run(body)


def test_noop_when_clean():
    section("② 無滯留 ＋ 無新變更 → 略過推送（不誤推）")

    def body(sb):
        head = sb.remote_head()
        before = sb.commit_count()
        ok(sb.sync() is True, "無事可做 → 回報成功")
        ok(sb.remote_head() == head, "遠端未變動")
        ok(sb.commit_count() == before, "未產生新 commit")
    _run(body)


def test_normal_change():
    section("③ 有新變更 → commit 並推送（既有行為回歸）")

    def body(sb):
        sb.write("data.json", '{"v": 2}\n')
        before = sb.commit_count()
        ok(sb.sync() is True, "推送成功")
        ok(sb.commit_count() == before + 1, "產生 1 筆新 commit")
        ok(sb.ahead() == 0 and sb.remote_head() == sb.local_head(), "遠端已同步")
    _run(body)


def test_retry_then_success():
    section("④ 遠端短暫拒收 2 次 → 退避重試後成功")

    def body(sb):
        sb.write("data.json", '{"v": 3}\n')
        sb.fail_next(2)
        ok(sb.sync() is True, "第 3 次推送成功（V1.3 只試 2 次會失敗）")
        ok(sb.ahead() == 0, "無滯留 commit")
    _run(body)


def test_all_retries_fail_then_self_heal():
    section("⑤ 重試全數失敗 → 下一次同步自動帶走（自癒）")

    attempts = len(git_sync.PUSH_RETRY_DELAYS) + 1

    def body(sb):
        sb.write("data.json", '{"v": 4}\n')
        sb.fail_next(attempts)                        # 剛好耗盡所有重試
        ok(sb.sync() is False, f"連續 {attempts} 次拒收 → 回報失敗")
        ok(sb.ahead() == 1, "commit 保留在本機，未遺失")

        # 模擬隔天孟恭 21:00：推另一個檔、戰報本身無新變更
        sb.write("other.json", '{"x": 1}\n')
        ok(git_sync.sync_to_github(files=["other.json"], commit_msg="mengong") is True,
           "下一支排程（推其他檔）推送成功")
        ok(sb.ahead() == 0, "前次滯留的戰報 commit 一併推出")
        ok(_git(sb.origin, "show", "main:data.json")[1] == '{"v": 4}', "遠端戰報內容為最新值")
    _run(body)


def test_timeout_budget():
    section("⑥ 逾時預算（防止日後改參數時互相踩到）")

    delays = git_sync.PUSH_RETRY_DELAYS
    ok(len(delays) >= 3, f"push 至少重試 3 次（目前 {len(delays) + 1} 次嘗試）")

    t = git_sync.GIT_CMD_TIMEOUT
    # 持鎖期間最壞：add/diff/commit/stash 等（視為 1 個指令逾時）＋ pull ＋ 每次 push 皆逾時 ＋ 退避總和
    worst_hold = t + t + t * (len(delays) + 1) + sum(delays)
    ok(worst_hold < git_sync.LOCK_STALE_SECONDS,
       f"持鎖最壞 {worst_hold} 秒 < 陳舊鎖門檻 {git_sync.LOCK_STALE_SECONDS} 秒（等待方不會誤回收）")

    need = git_sync.LOCK_WAIT_SECONDS + worst_hold
    ok(radar.SYNC_TIMEOUT_SECONDS >= need,
       f"radar 子程序逾時 {radar.SYNC_TIMEOUT_SECONDS} 秒 ≥ 等鎖 {git_sync.LOCK_WAIT_SECONDS} ＋ 持鎖 {worst_hold} ＝ {need} 秒")


TESTS = [
    test_stranded_commit_pushed,
    test_noop_when_clean,
    test_normal_change,
    test_retry_then_success,
    test_all_retries_fail_then_self_heal,
    test_timeout_budget,
]


def main():
    print("=" * 64)
    print("🧪 git_sync 推送流程離線回歸測試")
    print("=" * 64)
    for t in TESTS:
        t()
    print("\n" + "=" * 64)
    print(f"✅ 全數通過：{_checks} 項斷言")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
