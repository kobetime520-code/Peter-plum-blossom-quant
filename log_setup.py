"""
log_setup.py — 排程執行器共用的 logger 設定（稽核 E1／F-12）

問題：moly.py／grace_run.py／backtest_run.py 三支排程執行器各自以
      logging.basicConfig + FileHandler(mode='a') 寫同一支 moly.log，
      完全沒有輪替機制、只能單向成長；過去兩次歸檔（2026-07-04、07-09）
      都是編碼修復時順手做的人工動作，並非常態機制。

作法：改用 RotatingFileHandler，單檔上限 2 MB、保留 3 份（moly.log.1~3），
      三支執行器共用同一份設定，避免各寫各的再度漂移。

已知限制：週六 06:00 Moly-GraceDaily 與 Moly-BacktestWeekly 同時觸發、
      同寫 moly.log，Windows 檔案鎖可能使該次 rollover 失敗。maxBytes 設
      2 MB 讓 rollover 罕見；即使失敗也只影響輪替，不影響日誌寫入。
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOCAL_PATH, "moly.log")

MAX_BYTES = 2_000_000   # 單檔上限 2 MB
BACKUP_COUNT = 3        # 保留 moly.log.1 ~ moly.log.3


def setup_logging(tag="Moly 🌸"):
    """設定共用 logger：輪替檔案 + stdout。tag 為日誌前綴，用於分辨來源排程。"""
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
        delay=True,          # 延後開檔，降低與同時段排程搶檔案鎖的機會
    )
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s - {tag} - %(message)s",
        handlers=[handler, logging.StreamHandler(sys.stdout)],
    )
