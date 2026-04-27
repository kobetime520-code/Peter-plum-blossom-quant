# ==========================================
# 靜水流深戰情室：核心監控與全域雷達 V7.3
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

# --- 2. 魚池設定區  ---
POOL_SETTINGS = {
    "🔥 姊夫爆發小魚池": ["6155", "3357", "2493", "1514", "4967"],
    "🍁 楓大永動魚池": ["2308", "00923", "00910", "2327", "1785"],
    "🌟 彼神黃金魚池": ["3028", "2484", "3221", "8182", "8289"],
    "🔭 測試員觀察水域": ["2330", "2317", "2454", "2383", "3673", "5289", "5292", "6770", "4749"],
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

# 🎯 V7.3 新增：FinMind 股價前處理標準化函數
def normalize_finmind_price_df(df_finmind):
    """
    將 FinMind TaiwanStockPrice 的欄位名稱標準化，
    使其與 calculate_stock_data 內部邏輯相容。
    FinMind 欄位: date, close, volume (Trading_Volume)
    目標欄位: Close, Volume (與 Yahoo 格式一致)
    """
    if df_finmind is None or df_finmind.empty:
        return pd.DataFrame()
    
    df = df_finmind.copy()
    
    # 欄位重新命名對照表（涵蓋常見 FinMind 欄位變體）
    rename_map = {}
    col_lower = {c.lower(): c for c in df.columns}
    
    # 處理 Close 欄位
    for candidate in ['close', 'closing_price', 'Close']:
        if candidate.lower() in col_lower:
            rename_map[col_lower[candidate.lower()]] = 'Close'
            break
    
    # 處理 Volume 欄位
    for candidate in ['trading_volume', 'volume', 'Volume', 'Trading_Volume']:
        if candidate.lower() in col_lower:
            rename_map[col_lower[candidate.lower()]] = 'Volume'
            break
    
    if rename_map:
        df = df.rename(columns=rename_map)
    
    # 處理日期索引
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
    elif 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date').sort_index()
    
    # 確保數值型別正確
    if 'Close' in df.columns:
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    if 'Volume' in df.columns:
        df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
    
    # 清除無效資料
    required_cols = [c for c in ['Close', 'Volume'] if c in df.columns]
    if required_cols:
        df = df.dropna(subset=required_cols)
    
    return df

def calculate_stock_data(sid, name, industry, df_prices, df_inst, force_show=False):
    try:
        # 🎯 V7.3 前處理：自動偵測並標準化 FinMind 格式
        if df_prices is not None and not df_prices.empty:
            # 若欄位不含 'Close'，嘗試標準化（判斷為 FinMind 格式）
            if 'Close' not in df_prices.columns:
                df_prices = normalize_finmind_price_df(df_prices)

        # 處理無股價資料防呆
        if df_prices is None or df_prices.empty or len(df_prices) < 2:
            if force_show: return {"stock_id": sid, "stock_name": name, "industry": industry, "close": "無資料", "volume": 0, "inst_buy": 0, "foreign_buy": 0, "trust_buy": 0, "ma5": 0, "ma30": 0, "action": "靜候觀察", "target_price": 0, "stop_loss": 0}
            return None

        df_prices = df_prices.dropna(subset=['Close', 'Volume'])
        if df_prices.empty: return None

        # 計算量價與均線
        latest = df_prices.iloc[-1]
        close_price = round(float(latest['Close']), 2)
        ma5 = round(float(df_prices['Close'].rolling(window=5).mean().iloc[-1]), 2) if len(df_prices) >= 5 else close_price
        ma30 = round(float(df_prices['Close'].rolling(window=30).mean().iloc[-1]), 2) if len(df_prices) >= 30 else close_price
        vol_lots = int(float(latest['Volume']) / 1000) if pd.notna(latest['Volume']) else 0

        # 🎯 V7.1 籌碼細分核心邏輯（完整保留）
        inst_buy_30d = 0
        foreign_buy_30d = 0
        trust_buy_30d = 0
        
        if not df_inst.empty:
            df_inst['net_buy'] = df_inst.get('buy', 0) - df_inst.get('sell', 0)
            inst_buy_30d = int(df_inst['net_buy'].sum() / 1000)
            
            # 透過 name 欄位拆解外資與投信
            if 'name' in df_inst.columns:
                mask_foreign = df_inst['name'].astype(str).str.contains('外資|外陸資|Foreign', case=False, na=False)
                mask_trust = df_inst['name'].astype(str).str.contains('投信|Investment_Trust|Trust', case=False, na=False)
                
                foreign_buy_30d = int(df_inst[mask_foreign]['net_buy'].sum() / 1000)
                trust_buy_30d = int(df_inst[mask_trust]['net_buy'].sum() / 1000)

        action = "買入加碼" if close_price >= ma5 and inst_buy_30d > 0 else "靜候觀察"
        
        # 將外資與投信資料打包進回傳的 JSON 裡
        return {"stock_id": sid, "stock_name": name, "industry": industry, "close": close_price, "volume": vol_lots, "inst_buy": inst_buy_30d, "foreign_buy": foreign_buy_30d, "trust_buy": trust_buy_30d, "ma5": ma5, "ma30": ma30, "action": action, "target_price": round(close_price * 1.5, 2), "stop_loss": round(close_price * 0.9, 2)}
    except:
        if force_show: return {"stock_id": sid, "stock_name": name, "industry": industry, "close": "計算異常", "volume": 0, "inst_buy": 0, "foreign_buy": 0, "trust_buy": 0, "ma5": 0, "ma30": 0, "action": "靜候觀察", "target_price": 0, "stop_loss": 0}
        return None

def main():
    print("🌊 啟動彼我還楓姊夫戰情室 (V7.3 Yahoo粗篩+FinMind精濾 混合引擎版)...")
    taiwan_time = datetime.utcnow() + timedelta(hours=8)
    today_str = taiwan_time.strftime("%Y-%m-%d")
    start_30d = (taiwan_time - timedelta(days=45)).strftime("%Y-%m-%d")
    # 🎯 V7.3 新增：start_60d 確保 30MA 計算有足夠天數
    start_60d = (taiwan_time - timedelta(days=90)).strftime("%Y-%m-%d")
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

    # =====================================================================
    # 🎯 Yahoo Finance 全市場粗篩段（完全不動）
    # =====================================================================
    print(f"  - ⚡ 啟動原生下載資料 (共 {len(exact_tickers)} 檔)...")
    for i in range(0, len(exact_tickers), chunk_size):
        chunk = exact_tickers[i:i+chunk_size]
        print(f"    📦 載入進度: {i+1} ~ {min(i+chunk_size, len(exact_tickers))} 檔...")
        try:
            data = yf.download(chunk, period="60d", progress=False, group_by='ticker', threads=False)

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

    # =====================================================================
    # 🎯 V7.3 混合引擎核心：Yahoo 粗篩通過後，以 FinMind 精確股價製卡
    # =====================================================================
    market_pool = []
    added_market_sids = set()
    for sid in set(market_sids):
        # 第一關：Yahoo 粗篩（量能 & 站上30MA 條件用 Yahoo 快速判斷）
        df_yf = valid_dfs.get(sid)
        if df_yf is None or df_yf.empty: continue
        if sid in added_market_sids: continue
        try:
            latest_yf = df_yf.iloc[-1]
            if (float(latest_yf['Volume']) / 1000) >= 1000:
                ma30_yf = df_yf['Close'].rolling(window=30).mean().iloc[-1]
                if float(latest_yf['Close']) > ma30_yf:
                    # 第二關：FinMind 精確股價抓取（製卡用）
                    df_p_finmind = fetch_finmind("TaiwanStockPrice", start_60d, today_str, sid)
                    api_calls += 1
                    if df_p_finmind.empty:
                        time.sleep(1)
                        df_p_finmind = fetch_finmind("TaiwanStockPrice", start_60d, today_str, sid)
                        api_calls += 1
                    
                    # 第三關：FinMind 籌碼資料
                    df_i = fetch_finmind("TaiwanStockInstitutionalInvestorsBuySell", start_30d, today_str, sid)
                    api_calls += 1
                    if df_i.empty:
                        time.sleep(1)
                        df_i = fetch_finmind("TaiwanStockInstitutionalInvestorsBuySell", start_30d, today_str, sid)
                        api_calls += 1
                    time.sleep(0.2)
                    
                    ind = industry_map.get(sid, "未知產業")
                    # 🎯 製卡時傳入 FinMind 精確股價（取代原本的 Yahoo df_p）
                    s_data = calculate_stock_data(sid, name_map.get(sid, sid), ind, df_p_finmind, df_i)
                    if s_data and s_data['action'] == "買入加碼":
                        market_pool.append(s_data)
                        added_market_sids.add(sid)
        except: continue

    # 🎯 V7 核心升級：Date-Lock 日期防呆機制與向下相容（完整保留）
    today_ocean_sids = [s['stock_id'] for s in market_pool]
    new_history = {}
    
    for sid in today_ocean_sids:
        # 讀取舊資料，若無資料則給予預設值
        old_data = history.get(sid, {"count": 0, "last_date": ""})
        
        # 🛡️ 向下相容機制：如果讀到 V6 的舊格式 (純數字 int)，自動升級為 V7 字典格式
        if isinstance(old_data, int):
            old_data = {"count": old_data, "last_date": ""}
            
        count = old_data["count"]
        last_date = old_data["last_date"]
        
        # ⏳ 日期比對：只有當今天尚未被記錄過時，才允許 count + 1
        if last_date != today_str:
            count += 1
            
        # 寫入 V7 新結構
        new_history[sid] = {"count": count, "last_date": today_str}
        
        # 判斷是否晉升猛虎池
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
            
            # 🎯 V7.3：核心魚池也改用 FinMind 精確股價製卡
            # 嘗試先從快取取 Yahoo 資料做可用性確認（非必要，主要製卡用 FinMind）
            df_yf_cache = valid_dfs.get(sid)
            if df_yf_cache is None or df_yf_cache.empty:
                print(f"      - 快取未命中，啟動 {sid} 雙重火力補抓（Yahoo 備援）...")
                # 雙重火力補抓僅作為備援確認，製卡仍優先用 FinMind
                download_yf_data_single(sid, market_map)  # 保持原有補抓行為

            # FinMind 精確股價（製卡主力）
            df_p_finmind = fetch_finmind("TaiwanStockPrice", start_60d, today_str, sid)
            api_calls += 1
            if df_p_finmind.empty:
                time.sleep(1)
                df_p_finmind = fetch_finmind("TaiwanStockPrice", start_60d, today_str, sid)
                api_calls += 1

            # FinMind 籌碼資料
            df_i = fetch_finmind("TaiwanStockInstitutionalInvestorsBuySell", start_30d, today_str, sid)
            api_calls += 1
            if df_i.empty:
                time.sleep(1)
                df_i = fetch_finmind("TaiwanStockInstitutionalInvestorsBuySell", start_30d, today_str, sid)
                api_calls += 1

            ind = industry_map.get(sid, "未分類")
            # 🎯 製卡時傳入 FinMind 精確股價
            s_data = calculate_stock_data(sid, name_map.get(sid, sid), ind, df_p_finmind, df_i, force_show=True)
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
