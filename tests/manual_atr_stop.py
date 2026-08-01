# 任務2 驗證：波動度調整停損（ATR×2）— 獨立測試，零 FinMind、不推送
# ⚠️ 需 yfinance 連網，故不列入 run_all.py 的離線批次，改為手動執行
import sys, io, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import yfinance as yf
import radar  # 直接引用引擎函式

SAMPLES = [
    ("2330", ".TW", "台積電"),
    ("2484", ".TW", "希華"),
    ("6173", ".TW", "信昌電"),
    ("00910", ".TW", "第一金太空衛星"),
    ("3037", ".TW", "欣興"),
]

print(f"{'股號':<8}{'現價':>9}{'ATR14':>9}{'波動%':>8}  {'動態停損':>9}{'固定×0.9':>10}{'幅度%':>8}  模式")
print("-" * 78)
for sid, suf, name in SAMPLES:
    df = yf.Ticker(f"{sid}{suf}").history(period="60d")
    if df is None or df.empty:
        print(f"{sid:<8} 無資料")
        continue
    d = radar.calculate_stock_data(sid, name, "測試", df, pd.DataFrame(), force_show=True)
    close = d["close"]
    drop_pct = round((d["stop_loss"]/close - 1)*100, 2) if isinstance(close,(int,float)) and close else 0
    print(f"{sid:<8}{close:>9}{d['atr14']:>9}{d['atr_pct']:>8}  {d['stop_loss']:>9}{d['stop_loss_fixed']:>10}{drop_pct:>8}  {d['stop_loss_mode']}")

# 後備模式驗證：移除 High/Low 欄位
print("\n[VOL_FALLBACK 驗證] 移除 High/Low：")
df = yf.Ticker("2330.TW").history(period="60d")[["Close", "Volume"]]
d = radar.calculate_stock_data("2330", "台積電", "測試", df, pd.DataFrame(), force_show=True)
print(f"  ATR14={d['atr14']} 波動%={d['atr_pct']} 動態停損={d['stop_loss']} 模式={d['stop_loss_mode']}")
