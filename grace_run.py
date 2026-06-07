"""
grace_run.py — 每週日 Grace 題材分析排程執行器（任務4）
由 C:\\Moly\\grace_start.ps1 每週日 07:00 觸發
流程：執行 grace_theme_gen.py 產生 grace_theme_data.json → 呼叫 git_sync.py 推送
日誌：與 Moly 共用 moly.log（標記 [Grace]）
"""
import sys, io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
import logging
import subprocess

LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))
_log_file = os.path.join(LOCAL_PATH, "moly.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Moly 🌸 [Grace] - %(message)s',
    handlers=[
        logging.FileHandler(_log_file, encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout),
    ],
)

GENERATOR = os.path.join(LOCAL_PATH, "grace_theme_gen.py")
GIT_SYNC = os.path.join(LOCAL_PATH, "git_sync.py")


def main():
    logging.info("=== Grace 題材分析排程啟動（每週日 07:00）===")

    logging.info("🎯 執行 grace_theme_gen.py ...")
    gen = subprocess.run([sys.executable, GENERATOR], cwd=LOCAL_PATH,
                         encoding="utf-8", errors="replace")
    if gen.returncode != 0:
        logging.error("❌ grace_theme_gen.py 執行失敗（返回碼 %s），本次不推送。", gen.returncode)
        logging.info("=== Grace 排程結束（失敗）===")
        return
    logging.info("✅ grace_theme_data.json 產生完成。")

    logging.info("🔗 呼叫 git_sync.py 推送題材分析 ...")
    push = subprocess.run([sys.executable, GIT_SYNC], cwd=LOCAL_PATH,
                          encoding="utf-8", errors="replace")
    if push.returncode == 0:
        logging.info("✅ 題材分析已推送至 GitHub main。")
    else:
        logging.error("❌ git_sync.py 推送失敗（返回碼 %s），請手動執行：python git_sync.py", push.returncode)

    logging.info("=== Grace 排程結束 ===")


if __name__ == "__main__":
    main()
