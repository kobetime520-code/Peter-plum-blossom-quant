# ==========================================
# 靜水流深戰情室：核心監控與全域雷達 V7.5
# ==========================================
# V7.5 API 降載三劍客：
#   ① Yahoo MA5 前置預篩  → 市場掃描省 ~40% 呼叫
#   ② Yahoo 股價取代 FinMind（市場掃描 + 魚池）→ 每股節省 1 call
#   ③ TaiwanStockInfo 7 日快取 → 每週省 6 次
#   預估總降幅：430 → ~260 次（減少 ~40%）
# ==========================================
import yfinance as yf
import pandas as pd
import requests
import time
import json
import os
import logging
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger('yfinance')
logger.setLevel(logging.CRITICAL)

# --- 1. 金鑰與設定區 ---
# 🔐 V7.5 安全修正：Token 從環境變數讀取（不再硬碼）
FINMIND_TOKEN = os.environ.get("FINMIND_TOKEN", "")
HISTORY_FILE = "ocean_history.json"
CACHE_FILE = "finmind_cache.json"
INFO_CACHE_FILE = "finmind_info_cache.json"   # 🆕 V7.5：TaiwanStockInfo 獨立快取
INFO_CACHE_EXPIRY_DAYS = 7                    # 🆕 V7.5：股票基本資料 7 天更新一次

# --- 2. 魚池設定區 ---
POOL_SETTINGS = {
    "🔥 姊夫爆發小魚池": ["6155", "3357", "2493", "1514", "4967"],
    "🍁 楓大永動魚池": ["2308", "00923", "00910", "2327", "1785"],
    "🌟 彼神黃金魚池": ["3028", "2484", "3221", "8182", "8289"],
    "🔭 測試員觀察水域": ["2330", "2317", "2454", "2383", "3673", "5289", "5292", "3042", "4749"],
    "🐅 三日成猛虎水池": []
}

# =====================================================================
# 🎯 V7.4 全域快取與 API 計數器
# =====================================================================
_finmind_cache: dict = {}
_api_calls_count: int = 0


def fetch_finmind(dataset, start_date, end_date, data_id, retries=1):
    """
    發送 FinMind API 請求，內建本地快取機制。
    快取命中時直接回傳資料，不消耗 API 額度。
    快取 Key：{dataset}_{data_id}_{start_date}_{end_date}
    """
    global _finmind_cache, _api_calls_count

    cache_key = f"{dataset}_{data_id}_{start_date}_{end_date}"

    # ── 快取命中：直接回傳，不計入 API 次數 ──
    if cache_key in _finmind_cache:
        try:
            return pd.DataFrame(_finmind_cache[cache_key])
        except Exception:
            _finmind_cache.pop(cache_key, None)

    # ── 快取未命中：呼叫 API ──
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": dataset,
        "data_id": data_id,
        "start_date": start_date,
        "end_date": end_date,
        "token": FINMIND_TOKEN,
    }
    _api_calls_count += 1
    for attempt in range(retries + 1):
        try:
            res = requests.get(url, params=params, timeout=10)
            res_data = res.json()
            if res_data.get("msg") == "success":
                data_list = res_data.get("data", [])
                try:
                    _finmind_cache[cache_key] = data_list
                except Exception:
                    pass
                return pd.DataFrame(data_list)
            else:
                break
        except Exception:
            if attempt < retries:
                time.sleep(1)
    return pd.DataFrame()


# 🎯 雙重火力補抓機制 (Double-Tap Fallback)
def download_yf_data_single(sid, market_map, retries=3):
    m_type = str(market_map.get(str(sid), "")).lower()

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
            except Exception:
                pass
        time.sleep(1.5)
    return pd.DataFrame()


# 🎯 V7.3 新增：FinMind 股價前處理標準化函數
def normalize_finmind_price_df(df_finmind):
    """
    將 FinMind TaiwanStockPrice 的欄位名稱標準化，
    使其與 calculate_stock_data 內部邏輯相容。
    """
    if df_finmind is None or df_finmind.empty:
        return pd.DataFrame()

    df = df_finmind.copy()
    rename_map = {}
    col_lower = {c.lower(): c for c in df.columns}

    for candidate in ['close', 'closing_price', 'Close']:
        if candidate.lower() in col_lower:
            rename_map[col_lower[candidate.lower()]] = 'Close'
            break

    for candidate in ['trading_volume', 'volume', 'Volume', 'Trading_Volume']:
        if candidate.lower() in col_lower:
            rename_map[col_lower[candidate.lower()]] = 'Volume'
            break

    if rename_map:
        df = df.rename(columns=rename_map)

    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
    elif 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date').sort_index()

    if 'Close' in df.columns:
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    if 'Volume' in df.columns:
        df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')

    required_cols = [c for c in ['Close', 'Volume'] if c in df.columns]
    if required_cols:
        df = df.dropna(subset=required_cols)

    return df


def calculate_stock_data(sid, name, industry, df_prices, df_inst, force_show=False):
    try:
        if df_prices is not None and not df_prices.empty:
            if 'Close' not in df_prices.columns:
                df_prices = normalize_finmind_price_df(df_prices)

        if df_prices is None or df_prices.empty or len(df_prices) < 2:
            if force_show:
                return {"stock_id": sid, "stock_name": name, "industry": industry,
                        "close": "無資料", "volume": 0, "inst_buy": 0,
                        "foreign_buy": 0, "trust_buy": 0, "ma5": 0, "ma30": 0,
                        "action": "靜候觀察", "target_price": 0, "stop_loss": 0}
            return None

        df_prices = df_prices.dropna(subset=['Close', 'Volume'])
        if df_prices.empty:
            return None

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

            if 'name' in df_inst.columns:
                mask_foreign = df_inst['name'].astype(str).str.contains('外資|外陸資|Foreign', case=False, na=False)
                mask_trust = df_inst['name'].astype(str).str.contains('投信|Investment_Trust|Trust', case=False, na=False)
                foreign_buy_30d = int(df_inst[mask_foreign]['net_buy'].sum() / 1000)
                trust_buy_30d = int(df_inst[mask_trust]['net_buy'].sum() / 1000)

        action = "買入加碼" if close_price >= ma5 and inst_buy_30d > 0 else "靜候觀察"

        return {
            "stock_id": sid, "stock_name": name, "industry": industry,
            "close": close_price, "volume": vol_lots,
            "inst_buy": inst_buy_30d, "foreign_buy": foreign_buy_30d, "trust_buy": trust_buy_30d,
            "ma5": ma5, "ma30": ma30, "action": action,
            "target_price": round(close_price * 1.5, 2),
            "stop_loss": round(close_price * 0.9, 2),
        }
    except Exception:
        if force_show:
            return {"stock_id": sid, "stock_name": name, "industry": industry,
                    "close": "計算異常", "volume": 0, "inst_buy": 0,
                    "foreign_buy": 0, "trust_buy": 0, "ma5": 0, "ma30": 0,
                    "action": "靜候觀察", "target_price": 0, "stop_loss": 0}
        return None


def main():
    global _finmind_cache, _api_calls_count

    print("🌊 啟動彼我還楓姊夫戰情室 (V7.5 API三劍客降載版：MA5預篩＋Yahoo替代股價＋Info七日快取)...")

    # ── 載入本地快取（籌碼資料） ──────────────────────────────────────
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                _finmind_cache = json.load(f)
            print(f"  - 📦 快取載入成功，共 {len(_finmind_cache)} 筆已快取資料")
        else:
            print("  - 📦 無現有快取，本次將從零建立")
    except Exception:
        _finmind_cache = {}
        print("  - ⚠️ 快取讀取失敗，使用空快取繼續執行")

    taiwan_time = datetime.utcnow() + timedelta(hours=8)
    today_str = taiwan_time.strftime("%Y-%m-%d")
    start_30d = (taiwan_time - timedelta(days=45)).strftime("%Y-%m-%d")
    start_60d = (taiwan_time - timedelta(days=90)).strftime("%Y-%m-%d")

    # =====================================================================
    # 🆕 V7.5 優化③：TaiwanStockInfo 7 日快取
    # 股票基本資料（名稱、產業、市場別）幾乎不變，7天才重抓一次
    # =====================================================================
    df_info = None
    try:
        if os.path.exists(INFO_CACHE_FILE):
            with open(INFO_CACHE_FILE, 'r', encoding='utf-8') as f:
                info_cache = json.load(f)
            cache_date_str = info_cache.get("date", "2000-01-01")
            cache_date = datetime.strptime(cache_date_str, "%Y-%m-%d")
            age_days = (taiwan_time - cache_date).days
            if age_days < INFO_CACHE_EXPIRY_DAYS:
                df_info = pd.DataFrame(info_cache.get("data", []))
                print(f"  - 📋 TaiwanStockInfo 使用 {age_days} 天前快取（{cache_date_str}，尚有效，省 1 API 次）")
    except Exception:
        pass

    if df_info is None or df_info.empty:
        print("  - 📋 TaiwanStockInfo 快取已過期或不存在，重新抓取...")
        df_info = fetch_finmind("TaiwanStockInfo", "2020-01-01", today_str, "")
        if not df_info.empty:
            try:
                with open(INFO_CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump({
                        "date": today_str,
                        "data": df_info.to_dict('records')
                    }, f, ensure_ascii=False)
                print(f"  - 💾 TaiwanStockInfo 已快取至 {INFO_CACHE_FILE}（7天內免抓）")
            except Exception:
                pass

    if df_info is None or df_info.empty:
        print("❌ 無法取得股票清單，終止執行")
        return

    name_map = dict(zip(df_info['stock_id'].astype(str), df_info['stock_name']))
    industry_map = dict(zip(df_info['stock_id'].astype(str), df_info['industry_category']))
    market_map = dict(zip(df_info['stock_id'].astype(str), df_info['type']))

    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)

    print("🚢 正在掃描全市場 (精準狙擊模式)...")
    pure_stocks = df_info[
        (df_info['stock_id'].str.len() == 4) &
        (df_info['stock_id'].str.isdigit()) &
        (~df_info['industry_category'].str.contains('ETF|受益憑證', na=False))
    ]
    market_sids = pure_stocks['stock_id'].tolist()

    core_sids = []
    for tickers in POOL_SETTINGS.values():
        core_sids.extend(tickers)

    all_sids = list(set(market_sids + core_sids))

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
        chunk = exact_tickers[i:i + chunk_size]
        print(f"    📦 載入進度: {i+1} ~ {min(i+chunk_size, len(exact_tickers))} 檔...")
        try:
            data = yf.download(chunk, period="60d", progress=False, group_by='ticker', threads=False)

            if not data.empty:
                is_multi = isinstance(data.columns, pd.MultiIndex)
                for ticker in chunk:
                    sid = ticker.split(".")[0]
                    try:
                        if is_multi:
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
                    except Exception:
                        missing_sids.append(sid)
            else:
                for ticker in chunk:
                    missing_sids.append(ticker.split(".")[0])
        except Exception:
            for ticker in chunk:
                missing_sids.append(ticker.split(".")[0])
        time.sleep(1.0)

    print(f"  - 🎯 下載完成！成功取得 {len(valid_dfs)} 檔有效股價，進入雷達濾網...")

    # =====================================================================
    # 🎯 V7.5 混合引擎核心（市場掃描段）
    #    粗篩門檻（全用 Yahoo 計算，無 API 消耗）：
    #      ① 成交量 >= 1,500 張
    #      ② 收盤 > MA30
    #      ③ 🆕 收盤 >= MA5（前置 action 邏輯預判，跳過必敗的股）
    #    精篩：通過三關者，只呼叫 FinMind 籌碼（1 call/股）
    #          股價改用 Yahoo 取代 FinMind（省 1 call/股）
    # =====================================================================
    market_pool = []
    added_market_sids = set()
    yf_skipped_ma5 = 0     # 統計：被 MA5 預篩擋掉的數量
    yf_passed_filter = 0   # 統計：三關全過、真正呼叫 FinMind 的數量

    for sid in set(market_sids):
        df_yf = valid_dfs.get(sid)
        if df_yf is None or df_yf.empty:
            continue
        if sid in added_market_sids:
            continue
        try:
            latest_yf = df_yf.iloc[-1]
            close_yf = float(latest_yf['Close'])
            vol_lots_yf = float(latest_yf['Volume']) / 1000

            # 第一關：量能門檻（V7.4 縮圈戰術）
            if vol_lots_yf < 1500:
                continue

            # 第二關：收盤 > MA30（趨勢確認）
            ma30_yf = float(df_yf['Close'].rolling(window=30).mean().iloc[-1])
            if close_yf <= ma30_yf:
                continue

            # 🆕 第三關：收盤 >= MA5（action 前置預判）
            # action 邏輯為 close >= ma5 AND inst_buy > 0
            # 若 close < ma5，無論籌碼如何，action 必為「靜候觀察」→ 直接跳過
            ma5_yf = float(df_yf['Close'].rolling(window=5).mean().iloc[-1]) if len(df_yf) >= 5 else close_yf
            if close_yf < ma5_yf:
                yf_skipped_ma5 += 1
                continue

            # 三關全過：呼叫 FinMind 籌碼（僅 1 call，Yahoo 取代股價）
            yf_passed_filter += 1
            df_i = fetch_finmind("TaiwanStockInstitutionalInvestorsBuySell", start_30d, today_str, sid)
            if df_i.empty:
                time.sleep(1)
                df_i = fetch_finmind("TaiwanStockInstitutionalInvestorsBuySell", start_30d, today_str, sid)
            time.sleep(0.2)

            ind = industry_map.get(sid, "未知產業")
            # 🆕 直接用 Yahoo df 計算（不再額外呼叫 FinMind 股價）
            s_data = calculate_stock_data(sid, name_map.get(sid, sid), ind, df_yf, df_i)
            if s_data and s_data['action'] == "買入加碼":
                market_pool.append(s_data)
                added_market_sids.add(sid)
        except Exception:
            continue

    print(f"  - 📊 MA5 預篩：攔截 {yf_skipped_ma5} 支（必靜候），{yf_passed_filter} 支進入籌碼精篩")

    # 🎯 V7 核心升級：Date-Lock 日期防呆機制與向下相容（完整保留）
    today_ocean_sids = [s['stock_id'] for s in market_pool]
    new_history = {}

    for sid in today_ocean_sids:
        old_data = history.get(sid, {"count": 0, "last_date": ""})

        if isinstance(old_data, int):
            old_data = {"count": old_data, "last_date": ""}

        count = old_data["count"]
        last_date = old_data["last_date"]

        if last_date != today_str:
            count += 1

        new_history[sid] = {"count": count, "last_date": today_str}

        if count >= 3 and sid not in POOL_SETTINGS["🐅 三日成猛虎水池"]:
            POOL_SETTINGS["🐅 三日成猛虎水池"].append(sid)

    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)

    # =====================================================================
    # 🎯 V7.5 魚池監控段：Yahoo 股價優先，FinMind 只抓籌碼
    #    - Yahoo valid_dfs 中已有所有魚池股票的股價（大量下載時一併拿到）
    #    - 若 Yahoo 未命中才用雙重火力備援
    #    - FinMind 股價呼叫完全省略（每支魚池股省 1 call）
    # =====================================================================
    final_data_structure = {}
    for pool_name, tickers in POOL_SETTINGS.items():
        if pool_name == "🐅 三日成猛虎水池" and not tickers:
            continue
        print(f"🔍 監控中: {pool_name}...")
        results = []
        seen_in_pool = set()
        for sid in tickers:
            if sid in seen_in_pool:
                continue

            # 🆕 V7.5：優先用 Yahoo 股價，不呼叫 FinMind 股價
            df_price_to_use = valid_dfs.get(sid)
            if df_price_to_use is None or df_price_to_use.empty:
                print(f"      - Yahoo 未命中，啟動 {sid} 雙重火力補抓（Yahoo 備援）...")
                df_price_to_use = download_yf_data_single(sid, market_map)
                # 若 Yahoo 備援也失敗，才退回 FinMind 股價（最後防線）
                if df_price_to_use is None or df_price_to_use.empty:
                    print(f"      - Yahoo 備援失敗，改用 FinMind 股價（{sid}）...")
                    df_price_to_use = fetch_finmind("TaiwanStockPrice", start_60d, today_str, sid)
                    if df_price_to_use.empty:
                        time.sleep(1)
                        df_price_to_use = fetch_finmind("TaiwanStockPrice", start_60d, today_str, sid)

            # 只抓籌碼（1 call，Yahoo 已取代股價）
            df_i = fetch_finmind("TaiwanStockInstitutionalInvestorsBuySell", start_30d, today_str, sid)
            if df_i.empty:
                time.sleep(1)
                df_i = fetch_finmind("TaiwanStockInstitutionalInvestorsBuySell", start_30d, today_str, sid)

            ind = industry_map.get(sid, "未分類")
            s_data = calculate_stock_data(sid, name_map.get(sid, sid), ind, df_price_to_use, df_i, force_show=True)
            if s_data:
                results.append(s_data)
                seen_in_pool.add(sid)
            time.sleep(0.5)
        final_data_structure[pool_name] = results

    final_data_structure["🌊 汪洋大魚"] = market_pool

    # =====================================================================
    # 🎯 V7.6 前端儀表板數據預計算（供 index.html Chart.js 使用）
    # =====================================================================
    industry_counter = {}
    for s in market_pool:
        ind = s.get('industry', '未分類')
        industry_counter[ind] = industry_counter.get(ind, 0) + 1
    industry_dist = [{'industry': k, 'count': v}
                     for k, v in sorted(industry_counter.items(), key=lambda x: -x[1])[:12]]

    named_stocks = []
    for pname, pstocks in final_data_structure.items():
        if pname != "🌊 汪洋大魚":
            named_stocks.extend(pstocks)
    buy_n = sum(1 for s in named_stocks if s.get('action') == '買入加碼')
    watch_n = len(named_stocks) - buy_n

    pool_buy_stats = {}
    for pname, pstocks in final_data_structure.items():
        if pstocks and pname != "🌊 汪洋大魚":
            buy_p = sum(1 for s in pstocks if s.get('action') == '買入加碼')
            pool_buy_stats[pname] = {'total': len(pstocks), 'buy': buy_p}

    dashboard_stats = {
        'industry_distribution': industry_dist,
        'action_ratio': {'buy': buy_n, 'watch': watch_n},
        'pool_buy_stats': pool_buy_stats,
        'ocean_total': len(market_pool),
    }

    output = {
        "last_updated": taiwan_time.strftime("%Y/%m/%d %H:%M"),
        "api_cost_estimate": f"本次執行約消耗 {_api_calls_count} 次 FinMind API（快取節省不計入）",
        "dashboard_stats": dashboard_stats,
        "pools": final_data_structure,
    }
    with open("plum_blossom_data.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ── 儲存快取至本地 ────────────────────────────────────────────────
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(_finmind_cache, f, ensure_ascii=False, indent=2)
        print(f"  - 💾 快取已儲存，共 {len(_finmind_cache)} 筆（下次執行可直接命中）")
    except Exception:
        print("  - ⚠️ 快取儲存失敗，不影響本次結果")

    print(f"\n🎉 掃描完成！本次共消耗 FinMind API {_api_calls_count} 次（快取命中不計入）")
    print(f"   V7.6 儀表板數據：產業 {len(industry_dist)} 類、魚池多空 {buy_n}/{watch_n}")


if __name__ == "__main__":
    main()
