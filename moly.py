import subprocess
import time
import logging
import json
import os
from datetime import date

# 設定 Moly 的日誌格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - Moly 🌸 - %(message)s')

# 台灣國定假日（需每年更新，格式：YYYY-MM-DD）
TW_HOLIDAYS = {
    # 2026 國定假日
    "2026-01-01",  # 元旦
    "2026-01-27", "2026-01-28", "2026-01-29", "2026-01-30",
    "2026-01-31", "2026-02-02", "2026-02-03",  # 春節
    "2026-02-28",  # 和平紀念日
    "2026-04-03", "2026-04-04", "2026-04-05", "2026-04-06",  # 兒童節/清明
    "2026-05-01",  # 勞動節
    "2026-05-29", "2026-05-30", "2026-05-31",  # 端午節
    "2026-09-25", "2026-09-26", "2026-09-27",  # 中秋節
    "2026-10-10",  # 國慶日
}

def is_trading_day():
    """判斷今日是否為交易日（排除週末與國定假日）"""
    today = date.today()
    if today.weekday() >= 5:  # 週六=5, 週日=6
        logging.info(f"今日 {today} 為例假日，Moly 休息不執行。")
        return False
    if today.isoformat() in TW_HOLIDAYS:
        logging.info(f"今日 {today} 為國定假日，Moly 休息不執行。")
        return False
    return True

REPO     = "kobetime520-code/Peter-plum-blossom-quant"
WORKFLOW = "auto_radar.yml"
LOCAL_PATH = r"C:\Users\wangj\OneDrive\圖片\桌面\Team stock"

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
    if not is_trading_day():
        return
    if trigger_radar():
        if wait_for_completion():
            sync_local()
    logging.info("=== Moly 任務結束 ===")

if __name__ == "__main__":
    main()
