import subprocess
import logging
import os
import sys

# 設定 Moly 的日誌格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - Moly 🌸 - %(message)s')

# ============================================================
# 方案 B：本地主算核心（2026-05-04 架構重心轉移）
# 重度運算在本地端執行，GitHub 只負責展示最終戰報 JSON。
# 假日判斷由上層 C:\Moly\moly_start.ps1 統一處理，
# 本程式不重複實作 is_trading_day()，避免雙清單不同步。
#
# Git 推送邏輯統一由 radar.py 結尾呼叫的 git_sync.py 處理，
# moly.py 不重複執行 push，避免 non-fast-forward 衝突。
# ============================================================

LOCAL_PATH = r"C:\AIworkplace\AI Magic\Team stock"
RADAR_SCRIPT = os.path.join(LOCAL_PATH, "radar.py")


def run_radar():
    """本地直接執行 radar.py（內含 git_sync.py 自動推送，無需 moly.py 重複推送）"""
    logging.info("🚀 啟動本地雷達引擎...")
    logging.info(f"   執行腳本：{RADAR_SCRIPT}")

    result = subprocess.run(
        [sys.executable, RADAR_SCRIPT],
        cwd=LOCAL_PATH,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode == 0:
        logging.info("✅ 本地雷達掃描完成！戰報已產出並由 git_sync.py 推送至 GitHub。")
        return True
    else:
        logging.error("=" * 60)
        logging.error("❌ 【嚴重錯誤】radar.py 執行失敗！")
        logging.error(f"   錯誤代碼：{result.returncode}")
        logging.error("   請檢查 radar.py 的錯誤輸出，或手動執行：")
        logging.error(f"   python {RADAR_SCRIPT}")
        logging.error("=" * 60)
        return False


def main():
    logging.info("=== Moly 本地主算核心啟動（方案 B）===")

    if run_radar():
        logging.info("✅ 全流程完成：雷達掃描 → 戰報產出 → GitHub 同步（由 git_sync.py 執行）")
    else:
        logging.error("⚠️  雷達掃描失敗，本次不推送任何資料。")
        logging.error("    請確認 Python 環境、API Token 與網路連線後重試。")

    logging.info("=== Moly 任務結束 ===")


if __name__ == "__main__":
    main()
