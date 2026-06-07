"""
backtest_run.py — 每週回測排程執行器（任務1）
用途：每週六由 C:\\Moly\\backtest_start.ps1 觸發
流程：執行 backtest_generator.py 產生 backtest_report.json → 呼叫 git_sync.py 推送
日誌：與 Moly 共用 moly.log（標記 [Backtest]）
"""
import sys
import io

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import os
import logging
import subprocess

LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))
_log_file = os.path.join(LOCAL_PATH, "moly.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Moly 🌸 [Backtest] - %(message)s',
    handlers=[
        logging.FileHandler(_log_file, encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout),
    ],
)

GENERATOR = os.path.join(LOCAL_PATH, "backtest_generator.py")
GIT_SYNC = os.path.join(LOCAL_PATH, "git_sync.py")


def main():
    logging.info("=== 每週回測排程啟動（每週六 06:00）===")

    # Step 1：產生回測報告
    logging.info("📊 執行 backtest_generator.py ...")
    gen = subprocess.run(
        [sys.executable, GENERATOR], cwd=LOCAL_PATH,
        encoding="utf-8", errors="replace",
    )
    if gen.returncode != 0:
        logging.error("❌ backtest_generator.py 執行失敗（返回碼 %s），本次不推送。", gen.returncode)
        logging.info("=== 回測排程結束（失敗）===")
        return

    logging.info("✅ backtest_report.json 產生完成。")

    # Step 2：推送（重用 git_sync.py，含 rebase/衝突處理）
    logging.info("🔗 呼叫 git_sync.py 推送回測報告 ...")
    push = subprocess.run(
        [sys.executable, GIT_SYNC], cwd=LOCAL_PATH,
        encoding="utf-8", errors="replace",
    )
    if push.returncode == 0:
        logging.info("✅ 回測報告已推送至 GitHub main。")
    else:
        logging.error("❌ git_sync.py 推送失敗（返回碼 %s），請手動執行：python git_sync.py", push.returncode)

    logging.info("=== 回測排程結束 ===")


if __name__ == "__main__":
    main()
