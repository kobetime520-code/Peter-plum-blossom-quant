"""
tools/backfill_ocean_dates.py — 記憶海 dates 欄位一次性回補（V9.6，2026-10-18 Right）

用途：V9.6 猛虎晉升改看「近 28 天命中次數」，需要每支股票的逐日命中紀錄；
      V9.5 以前記憶海只存 count／last_date。本工具自 git 歷史逐版讀出
      ocean_history.json，每一版的 last_date 即為當次命中日，彙整成 dates。

起點 2026-07-07：與 2026-08-01 A2 回補的 W4 窗口一致（count 由該日起累計）。
真·僅追加：只新增 dates 欄位，count／last_date 與筆數一律不動。
校驗：len(dates) == count 者才寫入；不一致者只列出、不寫 dates
      （該筆會走 merge_ocean_history 的舊格式退回路徑，以累計 count 判斷）。

執行：python tools/backfill_ocean_dates.py            # 預演，只列統計
      python tools/backfill_ocean_dates.py --apply    # 寫回 ocean_history.json
不呼叫任何 API、不推送；寫回後由排程或 git_sync.py 推送。
"""
import json
import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE = os.path.join(REPO, "ocean_history.json")
SINCE = "2026-07-07"


def collect_dates(snapshots, since=SINCE):
    """snapshots：依時間排序的 ocean_history dict 序列 → {sid: 排序後的命中日清單}"""
    dates = {}
    for hist in snapshots:
        for sid, v in hist.items():
            ld = v.get("last_date", "") if isinstance(v, dict) else ""
            if ld and ld >= since:
                dates.setdefault(sid, set()).add(ld)
    return {sid: sorted(ds) for sid, ds in dates.items()}


def apply_dates(history, dates):
    """回傳 (new_history, filled, mismatches)；mismatches 為 [(sid, count, len(dates))]。
    已有 dates 的筆原樣保留（可重複執行）。"""
    new_history, filled, mismatches = {}, 0, []
    for sid, v in history.items():
        entry = dict(v) if isinstance(v, dict) else v
        if isinstance(entry, dict) and "dates" not in entry:
            ds = dates.get(sid, [])
            if len(ds) == entry.get("count", 0) and (not ds or ds[-1] == entry.get("last_date")):
                entry["dates"] = list(ds)
                filled += 1
            else:
                mismatches.append((sid, entry.get("count", 0), len(ds)))
        new_history[sid] = entry
    return new_history, filled, mismatches


def _git_snapshots(since=SINCE):
    def git(*a):
        return subprocess.run(["git", *a], cwd=REPO, capture_output=True).stdout
    log = git("log", "--reverse", f"--since={since}", "--format=%H",
              "--", "ocean_history.json").decode().split()
    for h in log:
        try:
            yield json.loads(git("show", f"{h}:ocean_history.json").decode("utf-8"))
        except Exception:
            continue


def main(argv):
    with open(HISTORY_FILE, encoding="utf-8") as f:
        history = json.load(f)
    snapshots = list(_git_snapshots()) + [history]   # 含工作區現況（未提交的最新一輪）
    dates = collect_dates(snapshots)
    new_history, filled, mismatches = apply_dates(history, dates)

    print(f"記憶海 {len(history)} 支｜git 版本 {len(snapshots) - 1} 個｜可回補 {filled} 支｜不一致 {len(mismatches)} 支")
    for sid, c, n in mismatches[:30]:
        print(f"  ⚠️ {sid}: count={c}，git 重建命中日 {n} 個 → 不寫 dates（退回累計判斷）")
    if len(new_history) != len(history):
        print("❌ 筆數改變，中止")
        return 1
    if "--apply" not in argv:
        print("（預演模式，未寫檔；加 --apply 寫回）")
        return 0
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)
    print(f"✅ 已寫回 {HISTORY_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
