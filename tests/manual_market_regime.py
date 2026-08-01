# 任務3 驗證：大盤環境過濾（^TWII vs MA60）— 獨立測試，零 FinMind、不推送
# ⚠️ 需 yfinance 連網取 ^TWII，故不列入 run_all.py 的離線批次，改為手動執行
import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import radar

print("=== 當前真實大盤環境判定 ===")
r = radar._calc_market_regime()
for k, v in r.items():
    print(f"  {k:>18} : {v}")

print("\n=== 三段式門檻對照（驗證分支邏輯）===")
print(f"{'環境':<6}{'量能門檻':>10}{'量比門檻':>10}{'score折扣':>10}")
print("-" * 40)
expected = {
    "多頭": (2000, 1.2, 1.00),
    "中性": (2500, 1.35, 0.92),
    "空頭": (3000, 1.5, 0.85),
}
for name, (vt, vr, sf) in expected.items():
    print(f"{name:<6}{vt:>10}{vr:>10}{sf:>10}")

print(f"\n當前環境 = {r['emoji']} {r['regime']}")
print(f"  → 本次掃描將套用：量能≥{r['vol_threshold']}張、量比≥{r['volratio_threshold']}、強勢評分×{r['score_factor']}")
print(f"  → 燈號說明：{r['note']}")

# 驗證 _SCORE_FACTOR 降權對 calculate_stock_data 的實際影響
print("\n=== score 降權實測（同一股票，多頭 vs 空頭因子）===")
import pandas as pd, yfinance as yf
df = yf.Ticker("2330.TW").history(period="60d")
df_i = pd.DataFrame()
radar._SCORE_FACTOR = 1.00
s_bull = radar.calculate_stock_data("2330", "台積電", "半導體", df, df_i, force_show=True)
radar._SCORE_FACTOR = 0.85
s_bear = radar.calculate_stock_data("2330", "台積電", "半導體", df, df_i, force_show=True)
radar._SCORE_FACTOR = 1.00  # 還原
print(f"  多頭(×1.00) strength_score = {s_bull['strength_score']}")
print(f"  空頭(×0.85) strength_score = {s_bear['strength_score']}（應 ≈ {round(s_bull['strength_score']*0.85)}）")
