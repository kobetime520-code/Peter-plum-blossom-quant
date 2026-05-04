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
# ============================================================

LOCAL_PATH = r"C:\Users\wangj\OneDrive\AI Magic\Team stock"
RADAR_SCRIPT = os.path.join(LOCAL_PATH, "radar.py")

# ⚠️ 嚴格管控：只推這三個資料檔，絕不推快取或機密
SAFE_FILES = [
    "plum_blossom_data.json",
    "ocean_history.json",
    "log_report.json"
]


def run_cmd(cmd, cwd=None):
    """執行終端機指令的輔助函數"""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        encoding="utf-8", errors="replace", cwd=cwd
    )
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()


def run_radar():
    """本地直接執行 radar.py，取代雲端 GitHub Actions"""
    logging.info("🚀 啟動本地雷達引擎...")
    logging.info(f"   執行腳本：{RADAR_SCRIPT}")

    result = subprocess.run(
        [sys.executable, RADAR_SCRIPT],
        cwd=LOCAL_PATH,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode == 0:
        logging.info("✅ 本地雷達掃描完成！戰報已產出。")
        return True
    else:
        logging.error("=" * 60)
        logging.error("❌ 【嚴重錯誤】radar.py 執行失敗！")
        logging.error(f"   錯誤代碼：{result.returncode}")
        logging.error("   請檢查 radar.py 的錯誤輸出，或手動執行：")
        logging.error(f"   python {RADAR_SCRIPT}")
        logging.error("=" * 60)
        return False


def push_results():
    """安全推送戰報到 GitHub（精準 add，絕不使用 git add .）"""
    logging.info("📤 準備安全推送戰報到 GitHub...")

    # 確認要推的檔案是否存在
    missing = [f for f in SAFE_FILES if not os.path.exists(os.path.join(LOCAL_PATH, f))]
    if missing:
        logging.error(f"❌ 以下戰報檔案不存在，中止推送：{missing}")
        return False

    # 精準 add：只推三個 JSON，防止 finmind_cache.json 或其他機密上傳
    add_cmd = "git add " + " ".join(SAFE_FILES)
    success, out, err = run_cmd(add_cmd, cwd=LOCAL_PATH)
    if not success:
        logging.error(f"❌ git add 失敗：{err}")
        return False

    # commit（若資料無變動則 gracefully 跳過）
    success, out, err = run_cmd(
        'git commit -m "Auto update daily report by local Moly"',
        cwd=LOCAL_PATH
    )
    if not success:
        if "nothing to commit" in out or "nothing to commit" in err:
            logging.info("ℹ️  資料無變動，本次略過 commit。")
            return True
        logging.error(f"❌ git commit 失敗：{err}")
        return False

    logging.info(f"✅ Commit 完成：{out[:80]}")

    # push
    success, out, err = run_cmd("git push origin main", cwd=LOCAL_PATH)
    if success:
        logging.info("✅ GitHub 戰報同步完成！開啟 index.html 即可查看最新戰況。")
        return True
    else:
        logging.error(f"❌ git push 失敗：{err}")
        return False


def main():
    logging.info("=== Moly 本地主算核心啟動（方案 B）===")

    if run_radar():
        push_results()
    else:
        logging.error("⚠️  雷達掃描失敗，本次不推送任何資料。")
        logging.error("    請確認 Python 環境、API Token 與網路連線後重試。")

    logging.info("=== Moly 任務結束 ===")


if __name__ == "__main__":
    main()
