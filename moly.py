import subprocess
import logging
import os
import sys
import json
from datetime import datetime

LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))
_log_file = os.path.join(LOCAL_PATH, "moly.log")
RADAR_RUN_LOG = os.path.join(LOCAL_PATH, "radar_run.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Moly 🌸 - %(message)s',
    handlers=[
        logging.FileHandler(_log_file, encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)

# ============================================================
# 方案 B：本地主算核心（2026-05-04 架構重心轉移）
# 重度運算在本地端執行，GitHub 只負責展示最終戰報 JSON。
# 假日判斷由上層 C:\Moly\moly_start.ps1 統一處理，
# 本程式不重複實作 is_trading_day()，避免雙清單不同步。
#
# Git 推送邏輯統一由 radar.py 結尾呼叫的 git_sync.py 處理，
# moly.py 不重複執行 push，避免 non-fast-forward 衝突。
# ============================================================

RADAR_SCRIPT = os.path.join(LOCAL_PATH, "radar.py")


def run_radar():
    """本地直接執行 radar.py（內含 git_sync.py 自動推送，無需 moly.py 重複推送）"""
    logging.info("🚀 啟動本地雷達引擎...")
    logging.info(f"   執行腳本：{RADAR_SCRIPT}")

    # 以 utf-8 環境啟動子程序，並將 radar.py 全部輸出落地至 radar_run.log，
    # 避免錯誤被吞、避免 Windows cp950 造成亂碼，供事後追因。
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    with open(RADAR_RUN_LOG, "w", encoding="utf-8") as f:
        result = subprocess.run(
            [sys.executable, RADAR_SCRIPT],
            cwd=LOCAL_PATH,
            env=env,
            stdout=f,
            stderr=subprocess.STDOUT
        )

    if result.returncode == 0:
        logging.info("✅ 本地雷達掃描完成！戰報已產出並由 git_sync.py 推送至 GitHub。")
        return True
    else:
        logging.error("=" * 60)
        logging.error("❌ 【嚴重錯誤】radar.py 執行失敗！")
        logging.error(f"   錯誤代碼：{result.returncode}")
        logging.error(f"   完整錯誤輸出見：{RADAR_RUN_LOG}")
        logging.error("   或手動執行重試：")
        logging.error(f"   python {RADAR_SCRIPT}")
        logging.error("=" * 60)
        return False


def _is_report_fresh():
    """檢查 log_report.json 的 last_update 是否為今日，防 radar.py 假成功早退。"""
    try:
        log_path = os.path.join(LOCAL_PATH, "log_report.json")
        with open(log_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        last = report.get("last_update", "")        # "2026-06-09 21:22:10"
        return last[:10] == datetime.now().strftime("%Y-%m-%d")
    except Exception:
        return False


def _check_push_status():
    """讀取 log_report.json，回傳 push_status 欄位（預設 OK）"""
    try:
        log_path = os.path.join(LOCAL_PATH, "log_report.json")
        with open(log_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        return report.get("push_status", "OK")
    except Exception:
        return "OK"


def main():
    logging.info("=== Moly 本地主算核心啟動（方案 B）===")

    if run_radar():
        # 第二道驗證：returncode==0 不代表戰報真的更新，需確認 log_report 為今日，
        # 否則視為 radar.py 假成功早退（2026-06-09 事件防呆）。
        if not _is_report_fresh():
            logging.error("=" * 60)
            logging.error("❌ 【假成功攔截】radar.py 回報退出碼 0，但戰報未更新為今日！")
            logging.error("   疑似 radar.py 捕捉例外後早退，戰報實際未產出。")
            logging.error(f"   完整輸出見：{RADAR_RUN_LOG}")
            logging.error(f"   請手動補救：python {RADAR_SCRIPT}")
            logging.error("=" * 60)
        else:
            push_status = _check_push_status()
            if push_status != "OK":
                logging.error("=" * 60)
                logging.error(f"❌ 【推送失敗】git_sync.py 回報狀態：{push_status}")
                logging.error("   戰報已產出，但 GitHub 未更新。")
                logging.error("   請手動執行：python git_sync.py")
                logging.error("=" * 60)
            else:
                logging.info("✅ 全流程完成：雷達掃描 → 戰報產出 → GitHub 同步（由 git_sync.py 執行）")
    else:
        logging.error("⚠️  雷達掃描失敗，本次不推送任何資料。")
        logging.error("    請確認 Python 環境、API Token 與網路連線後重試。")

    logging.info("=== Moly 任務結束 ===")


if __name__ == "__main__":
    main()
