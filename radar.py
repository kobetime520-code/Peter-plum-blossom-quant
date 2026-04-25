# ==========================================
# 靜水流深戰情室：核心監控與全域雷達 V7 (Test)
# ==========================================
import yfinance as yf
import pandas as pd
import requests
import time
import json
import os
import logging
from datetime import datetime, timedelta
# from google.colab import files
import warnings

# 抑制警告與 yfinance 內部報錯
warnings.filterwarnings('ignore')
logger = logging.getLogger('yfinance')
logger.setLevel(logging.CRITICAL)

# --- 1. 金鑰與設定區 ---
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMiAxNjo1Nzo0OSIsInVzZXJfaWQiOiJQZXRlckplZmYwMjI2IiwiZW1haWwiOiJrb2JldGltZTUyMEBnbWFpbC5jb20iLCJpcCI6Ijk0LjE1Ni4yMDUuMjQzIn0.UuDTYEvzoHk_qdW6mBElD_OfM3fVezky7X9dEFId3zg"
HISTORY_FILE = "ocean_history.json"

# --- 2. 魚池設定區 (🎯 已將 2409 替換為 2049 上銀) ---
POOL_SETTINGS = {
    "🔥 姊夫爆發小魚池": ["6155", "3357", "2049", "4576", "2323"],
    "🍁 楓大永動魚池": ["2308", "00923", "00910", "2327", "1785"],
    "🌟 彼神黃金魚池": ["3028", "2484", "3221", "8182", "8289"],
    "🔭 測試員觀察水域": ["3673", "5289", "5292", "6770", "4749"],
    "🐅 三日成猛虎水池": []
}

def fetch_finmind(dataset, start_date, end_date, data_id, retries=1):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {"dataset": dataset, "data_id": data_id, "start_date": start_date, "end_date": end_date, "token": FINMIND_TOKEN}
    for attempt in range(retries + 1):
        try:
            res = requests.get(url, params=params, timeout=10)
            res_data = res.json()
            if res_data.get("msg") == "success":
                return pd.DataFrame(res_data.get("data"))
            else:
                break
        except:
            if attempt < retries: time.sleep(1)
    return pd.DataFrame()

# 🎯 雙重火力補抓機制 (Double-Tap Fallback)
def download_yf_data_single(sid, market_map, retries=3):
    m_type = str(market_map.get(str(sid), "")).lower()

    # 判斷優先後綴
    if "tpex" in m_type or "上櫃" in m_type or "otc" in m_type:
        primary_suffix, secondary_suffix = ".TWO", ".TW"
    else:
        primary_suffix, secondary_suffix = ".TW", ".TWO"

    for i in range(retries):
        for suffix in [primary_suffix, secondary_suffix]:
            try:
                df = yf.Ticker(f"{sid}{suffix}").history(period="60d")
                if not df.empty and 'Close' in df.columns:
                    df = df.dropna(subset=['Close', 'Volume'])
                    if not df.empty and len(df) >= 30:
                        return df
            except:
                pass
        time.sleep(1.5)
    return pd.DataFrame()

def calculate_stock_data(sid, name, industry, df_prices, df_inst, force_show=False):
    try:
        if df_prices is None or df_prices.empty or len(df_prices) < 2:
            if force_show: return {"stock_id": sid, "stock_name": name, "industry": industry, "close": "無資料", "volume": 0, "inst_buy": 0, "ma5": 0, "ma30": 0, "action": "靜候觀察", "target_price": 0, "stop_loss": 0}
            return None

        df_prices = df_prices.dropna(subset=['Close', 'Volume'])
        if df_prices.empty: return None

        latest = df_prices.iloc[-1]
        close_price = round(float(latest['Close']), 2)
        ma5 = round(float(df_prices['Close'].rolling(window=5).mean().iloc[-1]), 2) if len(df_prices) >= 5 else close_price
        ma30 = round(float(df_prices['Close'].rolling(window=30).mean().iloc[-1]), 2) if len(df_prices) >= 30 else close_price
        vol_lots = int(float(latest['Volume']) / 1000) if pd.notna(latest['Volume']) else 0

        inst_buy_30d = 0
        if not df_inst.empty:
            df_inst['net_buy'] = df_inst.get('buy', 0) - df_inst.get('sell', 0)
            inst_buy_30d = int(df_inst['net_buy'].sum() / 1000)

        action = "買入加碼" if close_price >= ma5 and inst_buy_30d > 0 else "靜候觀察"
        return {"stock_id": sid, "stock_name": name, "industry": industry, "close": close_price, "volume": vol_lots, "inst_buy": inst_buy_30d, "ma5": ma5, "ma30": ma30, "action": action, "target_price": round(close_price * 1.5, 2), "stop_loss": round(close_price * 0.9, 2)}
    except:
        if force_show: return {"stock_id": sid, "stock_name": name, "industry": industry, "close": "計算異常", "volume": 0, "inst_buy": 0, "ma5": 0, "ma30": 0, "action": "靜候觀察", "target_price": 0, "stop_loss": 0}
        return None

def main():
    print("🌊 啟動彼我還楓姊夫戰情室 (V6.9.7 無盲區精準狙擊版)...")
    taiwan_time = datetime.utcnow() + timedelta(hours=8)
    today_str = taiwan_time.strftime("%Y-%m-%d")
    start_30d = (taiwan_time - timedelta(days=45)).strftime("%Y-%m-%d")
    api_calls = 0

    df_info = fetch_finmind("TaiwanStockInfo", "2020-01-01", today_str, "")
    api_calls += 1
    if df_info.empty: return

    name_map = dict(zip(df_info['stock_id'].astype(str), df_info['stock_name']))
    industry_map = dict(zip(df_info['stock_id'].astype(str), df_info['industry_category']))
    market_map = dict(zip(df_info['stock_id'].astype(str), df_info['type']))

    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f: history = json.load(f)

    print("🚢 正在掃描全市場 (精準狙擊模式)...")
    pure_stocks = df_info[(df_info['stock_id'].str.len() == 4) & (df_info['stock_id'].str.isdigit()) & (~df_info['industry_category'].str.contains('ETF|受益憑證', na=False))]
    market_sids = pure_stocks['stock_id'].tolist()

    core_sids = []
    for tickers in POOL_SETTINGS.values():
        core_sids.extend(tickers)

    all_sids = list(set(market_sids + core_sids))

    # 🎯 多重語義解析：100% 精準捕捉上市櫃
    exact_tickers = []
    for sid in all_sids:
        m_type = str(market_map.get(str(sid), "")).lower()
        if "tpex" in m_type or "上櫃" in m_type or "otc" in m_type:
            exact_tickers.append(f"{sid}.TWO")
        else:
            exact_tickers.append(f"{sid}.TW")

    valid_dfs = {}
    missing_sids = []
    chunk_size = 150

    print(f"  - ⚡ 啟動原生下載資料 (共 {len(exact_tickers)} 檔)...")
    for i in range(0, len(exact_tickers), chunk_size):
        chunk = exact_tickers[i:i+chunk_size]
        print(f"    📦 載入進度: {i+1} ~ {min(i+chunk_size, len(exact_tickers))} 檔...")
        try:
            data = yf.download(chunk, period="60d", progress=False, group_by='ticker', threads=True)

            if not data.empty:
                is_multi = isinstance(data.columns, pd.MultiIndex)
                for ticker in chunk:
                    sid = ticker.split(".")[0]
                    try:
                        if is_multi:
                            # 🛡️ 更安全的 MultiIndex 提取法
                            if ticker in data.columns.get_level_values(0):
                                df = data[ticker]
                            else:
                                df = pd.DataFrame()
                        else:
                            df = data if len(chunk) == 1 else pd.DataFrame()

                        if 'Close' in df.columns and 'Volume' in df.columns:
                            df = df.dropna(subset=['Close', 'Volume'])
                            if not df.empty and len(df) >= 30:
                                valid_dfs[sid] = df
                            else:
                                missing_sids.append(sid)
                        else:
                            missing_sids.append(sid)
                    except:
                        missing_sids.append(sid)
            else:
                for ticker in chunk: missing_sids.append(ticker.split(".")[0])
        except Exception:
            for ticker in chunk: missing_sids.append(ticker.split(".")[0])
        time.sleep(1.0)

    print(f"  - 🎯 下載完成！成功取得 {len(valid_dfs)} 檔有效股價，進入雷達濾網...")

    market_pool = []
    added_market_sids = set()
    for sid in set(market_sids):
        df = valid_dfs.get(sid)
        if df is None or df.empty: continue
        if sid in added_market_sids: continue
        try:
            latest = df.iloc[-1]
            if (float(latest['Volume']) / 1000) >= 1000:
                ma30 = df['Close'].rolling(window=30).mean().iloc[-1]
                if float(latest['Close']) > ma30:
                    df_i = fetch_finmind("TaiwanStockInstitutionalInvestorsBuySell", start_30d, today_str, sid)
                    api_calls += 1
                    if df_i.empty:
                        time.sleep(1)
                        df_i = fetch_finmind("TaiwanStockInstitutionalInvestorsBuySell", start_30d, today_str, sid)
                        api_calls += 1
                    time.sleep(0.2)
                    ind = industry_map.get(sid, "未知產業")
                    s_data = calculate_stock_data(sid, name_map.get(sid, sid), ind, df, df_i)
                    if s_data and s_data['action'] == "買入加碼":
                        market_pool.append(s_data)
                        added_market_sids.add(sid)
        except: continue

    today_ocean_sids = [s['stock_id'] for s in market_pool]
    new_history = {}
    for sid in today_ocean_sids:
        count = history.get(sid, 0) + 1
        new_history[sid] = count
        if count >= 3 and sid not in POOL_SETTINGS["🐅 三日成猛虎水池"]:
            POOL_SETTINGS["🐅 三日成猛虎水池"].append(sid)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f: json.dump(new_history, f, ensure_ascii=False, indent=2)

    final_data_structure = {}
    for pool_name, tickers in POOL_SETTINGS.items():
        if pool_name == "🐅 三日成猛虎水池" and not tickers: continue
        print(f"🔍 監控中: {pool_name}...")
        results = []
        seen_in_pool = set()
        for sid in tickers:
            if sid in seen_in_pool: continue
            df_p = valid_dfs.get(sid)
            if df_p is None or df_p.empty:
                print(f"      - 快取未命中，啟動 {sid} 雙重火力補抓...")
                df_p = download_yf_data_single(sid, market_map)

            df_i = fetch_finmind("TaiwanStockInstitutionalInvestorsBuySell", start_30d, today_str, sid)
            api_calls += 1
            if df_i.empty:
                time.sleep(1)
                df_i = fetch_finmind("TaiwanStockInstitutionalInvestorsBuySell", start_30d, today_str, sid)
                api_calls += 1

            ind = industry_map.get(sid, "未分類")
            s_data = calculate_stock_data(sid, name_map.get(sid, sid), ind, df_p, df_i, force_show=True)
            if s_data:
                results.append(s_data)
                seen_in_pool.add(sid)
            time.sleep(0.5)
        final_data_structure[pool_name] = results

    final_data_structure["🌊 汪洋大魚"] = market_pool
    output = {
        "last_updated": taiwan_time.strftime("%Y/%m/%d %H:%M"),
        "api_cost_estimate": f"本次執行約消耗 {api_calls} 次 FinMind API",
        "pools": final_data_structure
    }
    with open("plum_blossom_data.json", 'w', encoding='utf-8') as f: json.dump(output, f, ensure_ascii=False, indent=2)
    # files.download("plum_blossom_data.json"); # files.download(HISTORY_FILE)
    print(f"\n🎉 掃描完成！本次掃描共計消耗 FinMind API 約 {api_calls} 次！")

if __name__ == "__main__":
    main()
