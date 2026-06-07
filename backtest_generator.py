# ==========================================
# 彼夫有責戰情室：回測績效產生器 V1.0（任務1 路線A 持股回顧版）
# ==========================================
# 目的：對指定魚池「目前成員」計算 5 / 30 / 126 交易日持有回顧績效
#   - 勝率（正報酬比例）
#   - 平均報酬（%）
#   - 超額報酬（魚池平均報酬 − 同期加權指數 ^TWII 報酬，%）
# 資料來源：純 yfinance（零 FinMind API 消耗）
# 範圍：🌟彼神黃金 / 🔥姊夫爆發 / 🍁楓大永動 / 🔭測試員觀察 / 🃏被動卡娃
#       （排除 🌊汪洋大魚、🐅三日成猛虎）
# 限制【資料】：採「當前成員」回顧，存在存活者偏誤，屬持股回顧而非歷史選股回測。
# 輸出：backtest_report.json
# ==========================================
import sys
import io

# 強制 UTF-8 輸出，防止 Windows CP950 終端對 emoji 拋 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import json
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
import warnings

warnings.filterwarnings("ignore")

# --- 設定區 ---
PLUM_FILE = "plum_blossom_data.json"
OUTPUT_FILE = "backtest_report.json"
BENCHMARK = "^TWII"  # 加權指數
WINDOWS = [5, 30, 126]  # 交易日窗格
WINDOW_LABELS = {5: "5日", 30: "30日", 126: "126日"}

# 納入回測的魚池（其餘一律排除）
TARGET_POOLS = [
    "🌟 彼神黃金魚池",
    "🔥 姊夫爆發小魚池",
    "🍁 楓大永動魚池",
    "🔭 測試員觀察水域",
    "🃏 被動卡娃魚池",
]


def fetch_close_series(ticker_no_suffix, retries=2):
    """抓取近一年日收盤序列，自動嘗試 .TW / .TWO 後綴；回傳 pd.Series（index=日期）。"""
    for _ in range(retries):
        for suffix in (".TW", ".TWO"):
            try:
                df = yf.Ticker(f"{ticker_no_suffix}{suffix}").history(period="1y")
                if df is not None and not df.empty and "Close" in df.columns:
                    s = df["Close"].dropna()
                    if len(s) >= 6:  # 至少要能算出最短窗格
                        return s
            except Exception:
                pass
        time.sleep(1.0)
    return pd.Series(dtype="float64")


def fetch_benchmark_series(retries=3):
    """抓取加權指數收盤序列。"""
    for _ in range(retries):
        try:
            df = yf.Ticker(BENCHMARK).history(period="1y")
            if df is not None and not df.empty and "Close" in df.columns:
                s = df["Close"].dropna()
                if len(s) >= 6:
                    return s
        except Exception:
            pass
        time.sleep(1.5)
    return pd.Series(dtype="float64")


def window_return(series: pd.Series, window: int):
    """以 entry = 倒數第 (window+1) 筆收盤、exit = 最新收盤，計算報酬（%）。
    資料不足回傳 None。"""
    if series is None or len(series) < window + 1:
        return None
    entry = float(series.iloc[-(window + 1)])
    exit_ = float(series.iloc[-1])
    if entry <= 0:
        return None
    return round((exit_ / entry - 1.0) * 100, 2)


def main():
    tw_now = datetime.utcnow() + timedelta(hours=8)
    print("🌊 啟動回測績效產生器 V1.0（持股回顧版，純 yfinance）...")

    # 1. 讀取目前魚池成員
    try:
        with open(PLUM_FILE, "r", encoding="utf-8") as f:
            plum = json.load(f)
    except Exception as e:
        print(f"❌ 無法讀取 {PLUM_FILE}：{e}")
        return
    pools = plum.get("pools", {})

    # 蒐集所有需要的股號（去重，保留名稱）
    members = {}  # pool_name -> [(sid, name)]
    all_ids = {}  # sid -> name
    for pname in TARGET_POOLS:
        lst = []
        for s in pools.get(pname, []):
            sid = str(s.get("stock_id", "")).strip()
            name = s.get("stock_name", sid)
            if not sid:
                continue
            lst.append((sid, name))
            all_ids[sid] = name
        members[pname] = lst
        print(f"  - 📋 {pname}：{len(lst)} 支")

    if not all_ids:
        print("❌ 目標魚池無任何成員，終止。")
        return

    # 2. 抓基準（加權指數）
    print(f"  - 📈 抓取基準指數 {BENCHMARK} ...")
    bench = fetch_benchmark_series()
    bench_returns = {}
    for w in WINDOWS:
        bench_returns[str(w)] = window_return(bench, w)
    print(f"    基準報酬：{ {WINDOW_LABELS[w]: bench_returns[str(w)] for w in WINDOWS} }")

    # 3. 抓每支個股收盤序列（一次抓、各窗格共用）
    print(f"  - 📥 抓取 {len(all_ids)} 支個股歷史價（去重，各魚池共用）...")
    series_cache = {}
    for i, sid in enumerate(all_ids, 1):
        series_cache[sid] = fetch_close_series(sid)
        ok = "✓" if len(series_cache[sid]) else "✗"
        print(f"    [{i}/{len(all_ids)}] {sid} {ok} ({len(series_cache[sid])} 筆)")

    # 4. 各魚池 × 各窗格彙總
    out_pools = {}
    for pname in TARGET_POOLS:
        out_pools[pname] = {}
        for w in WINDOWS:
            details = []
            for sid, name in members[pname]:
                ret = window_return(series_cache.get(sid), w)
                if ret is None:
                    continue
                b = bench_returns.get(str(w))
                excess = round(ret - b, 2) if b is not None else None
                details.append({
                    "stock_id": sid,
                    "stock_name": name,
                    "return": ret,
                    "excess": excess,
                })
            n = len(details)
            if n > 0:
                wins = sum(1 for d in details if d["return"] > 0)
                avg_ret = round(sum(d["return"] for d in details) / n, 2)
                b = bench_returns.get(str(w))
                avg_excess = round(avg_ret - b, 2) if b is not None else None
                win_rate = round(wins / n * 100, 1)
            else:
                avg_ret = None
                avg_excess = None
                win_rate = None
            # 個股明細依報酬高到低排序
            details.sort(key=lambda x: x["return"], reverse=True)
            out_pools[pname][str(w)] = {
                "win_rate": win_rate,
                "avg_return": avg_ret,
                "excess_return": avg_excess,
                "n": n,
                "details": details,
            }

    report = {
        "generated_at": tw_now.strftime("%Y/%m/%d %H:%M"),
        "method": "持股回顧版（當前成員，存活者偏誤；非歷史選股回測）",
        "benchmark": BENCHMARK,
        "windows": [str(w) for w in WINDOWS],
        "window_labels": {str(w): WINDOW_LABELS[w] for w in WINDOWS},
        "benchmark_returns": bench_returns,
        "pools": out_pools,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 回測完成，已輸出 {OUTPUT_FILE}")
    for pname in TARGET_POOLS:
        row = out_pools[pname]
        seg = " | ".join(
            f"{WINDOW_LABELS[w]} 勝率{row[str(w)]['win_rate']}% 均報{row[str(w)]['avg_return']}%"
            for w in WINDOWS
        )
        print(f"  {pname}：{seg}")


if __name__ == "__main__":
    main()
