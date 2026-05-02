import subprocess
import time
import logging
import json
import os

# 設定 Moly 的日誌格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - Moly 🌸 - %(message)s')

# ============================================================
# 注意：假日判斷由上層 C:\Moly\moly_start.ps1 統一處理
#   - 該 PS1 含 TWSE 公告之完整休市日清單（含補假）
#   - PS1 過濾後才會啟動 moly.py
# 因此此處不再重複實作 is_trading_day()，避免雙清單不同步。
# ============================================================

REPO     = "kobetime520-code/Peter-plum-blossom-quant"
WORKFLOW = "auto_radar.yml"
LOCAL_PATH = r"C:\Users\wangj\OneDrive\桌面\Team stock"

# gh CLI 完整路徑（Task Scheduler 不繼承用戶 PATH，需寫死）
GH = r"C:\Program Files\GitHub CLI\gh.exe"

def run_cmd(cmd):
    """執行終端機指令的輔助函數"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    return result.returncode == 0, result.stdout.strip()

def trigger_radar():
    logging.info("正在喚醒 GitHub 雲端無人機...")
    success, output = run_cmd(f'"{GH}" workflow run {WORKFLOW} --repo {REPO}')
    if success:
        logging.info("✅ 成功發射指令！無人機已起飛。")
        return True
    else:
        logging.error("❌ 觸發失敗，請檢查是否已登入 GitHub CLI (輸入 gh auth login)。")
        return False

def wait_for_completion():
    logging.info("⏳ 開始監控戰情室運算進度，預計需要 3~5 分鐘...")
    time.sleep(15)  # 等待 GitHub 初始化任務

    while True:
        # 查詢最新一次的任務狀態
        cmd = f'"{GH}" run list --workflow={WORKFLOW} --repo {REPO} --limit 1 --json status,conclusion'
        success, output = run_cmd(cmd)

        if success and output:
            try:
                data = json.loads(output)[0]
                status = data.get("status")
                conclusion = data.get("conclusion")

                if status == "completed":
                    if conclusion == "success":
                        logging.info("🎉 雲端運算完成！戰報已產出。")
                        return True
                    else:
                        logging.error(f"⚠️ 執行結束，但出現異常狀態: {conclusion}")
                        return False
                else:
                    logging.info("🔄 雲端正在拼命運算中，請稍候...")
            except Exception as e:
                pass

        # 每 30 秒檢查一次
        time.sleep(30)

def sync_local():
    logging.info("📥 正在把最新戰報同步回本地基地...")
    os.chdir(LOCAL_PATH)
    # fetch 後強制以雲端為主（雲端永遠獲勝）
    run_cmd("git fetch origin main")
    success, output = run_cmd("git reset --hard origin/main")
    if success:
        logging.info("✅ 本地資料已更新到最新版本！你可以開啟 index.html 看了。")
    else:
        logging.error("❌ 同步失敗，請確認目前是否有 Git 衝突。")

def main():
    logging.info("=== Moly 自動排程助理啟動 ===")
    if trigger_radar():
        if wait_for_completion():
            sync_local()
    logging.info("=== Moly 任務結束 ===")

if __name__ == "__main__":
    main()
