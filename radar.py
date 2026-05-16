# ==========================================
# 靜水流深戰情室：核心監控與全域雷達 V8.6
# ==========================================
# V7.5 API 降載三劍客：
#   ① Yahoo MA5 前置預篩  → 市場掃描省 ~40% 呼叫
#   ② Yahoo 股價取代 FinMind（市場掃描 + 魚池）→ 每股節省 1 call
#   ③ TaiwanStockInfo 7 日快取 → 每週省 6 次
#   預估總降幅：430 → ~260 次（減少 ~40%）
# V8.6 選股法則升級（零 API 消耗）：
#   ④ theme_tag：產業題材標籤（Grace 規格，由 industry_category 對應）
#   ⑤ sweet_buy_low / sweet_buy_high：甜蜜買進區間（Joe 計算法，MA5/MA10 中間帶）
#   ⑥ first_target：第一停利點（close × 1.15，+15%）
#   ⑦ 圖片法則：量比價先，量增價漲確認做多，題材優先過濾
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

import yfinance as yf
import pandas as pd
import requests
import time
import json
import os
import subprocess
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
CACHE_TTL_HOURS = 30                          # 🆕 V7.8：FinMind 快取有效期（30 小時，確保昨日資料今日仍可命中）
LOG_REPORT_FILE = "log_report.json"           # 🆕 V7.9：維運日誌輸出路徑（供 Zoey 儀表板讀取）

# --- 2. 魚池設定區 ---
POOL_SETTINGS = {
    "🔥 姊夫爆發小魚池": ["6155", "3060", "3236", "1513", "1519", "1605"],
    "🍁 楓大永動魚池": ["2308", "00923", "00910", "2327", "1785", "2344", "6485"],
    "🌟 彼神黃金魚池": ["3028", "2484", "3221", "8182", "8289", "3042"],
    "🔭 測試員觀察水域": ["5289", "5292", "4749", "6770", "1711", "8299", "3673", "3675"],
    "🐅 三日成猛虎水池": []
}

# =====================================================================
# 🎯 V7.4 全域快取與 API 計數器
# =====================================================================
_finmind_cache: dict = {}
_api_calls_count: int = 0      # FinMind API 實際呼叫次數（快取未命中）
_cache_hits_count: int = 0     # 🆕 V7.9：快取命中次數
_stocks_processed_count: int = 0  # 🆕 V7.9：成功處理的股票檔數


def _save_cache_to_disk():
    """🆕 V7.8：即時將記憶體快取寫入 finmind_cache.json（持久化）"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(_finmind_cache, f, ensure_ascii=False)
    except Exception:
        pass  # 寫盤失敗不中斷主流程


def _write_log_report(taiwan_time, stocks_processed=0, status="Success"):
    """🆕 V7.9：產出維運日誌 log_report.json（供 Zoey 儀表板讀取）"""
    try:
        report = {
            "last_update": taiwan_time.strftime("%Y-%m-%d %H:%M:%S"),
            "api_usage_count": _api_calls_count,
            "stocks_processed": stocks_processed,
            "cache_hits": _cache_hits_count,
            "status": status,
        }
        with open(LOG_REPORT_FILE, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"  - 📝 維運日誌已寫出：{LOG_REPORT_FILE}")
    except Exception as e:
        print(f"  - ⚠️ 維運日誌寫出失敗：{e}")


def fetch_finmind(dataset, start_date, end_date, data_id, retries=2):
    """
    發送 FinMind API 請求，內建本地快取機制。
    快取命中時直接回傳資料，不消耗 API 額度。
    快取 Key：{dataset}_{data_id}_{start_date}_{end_date}
    🆕 V7.7：重試邏輯完整封裝於函式內（retries=2），API 失敗或回傳非 success
             時自動等待 1 秒後重試，外部呼叫端無需再重複呼叫。
    """
    global _finmind_cache, _api_calls_count, _cache_hits_count

    cache_key = f"{dataset}_{data_id}_{start_date}_{end_date}"

    # ── 快取命中：直接回傳，不計入 API 次數 ──
    if cache_key in _finmind_cache:
        try:
            entry = _finmind_cache[cache_key]
            # 🆕 V7.8：相容新格式 {ts, data} 與舊格式 list
            if isinstance(entry, dict) and "data" in entry:
                _cache_hits_count += 1  # 🆕 V7.9
                return pd.DataFrame(entry["data"])
            elif isinstance(entry, list):
                _cache_hits_count += 1  # 🆕 V7.9
                return pd.DataFrame(entry)
        except Exception:
            _finmind_cache.pop(cache_key, None)

    # ── 快取未命中：呼叫 API（含完整重試） ──
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
            res = requests.get(url, params=params, timeout=15)
            res.raise_for_status()
            res_data = res.json()
            if res_data.get("msg") == "success":
                data_list = res_data.get("data", [])
                try:
                    # 🆕 V7.8：含時間戳的新格式，支援 TTL 清理
                    _finmind_cache[cache_key] = {
                        "ts": datetime.utcnow().isoformat(),
                        "data": data_list
                    }
                    _save_cache_to_disk()  # 🆕 V7.8：即時寫盤，防止中途中斷遺失快取
                except Exception:
                    pass
                return pd.DataFrame(data_list)
            else:
                # API 回傳非 success，等待後重試（不直接 break）
                if attempt < retries:
                    time.sleep(1)
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                time.sleep(1)
            else:
                print(f"  ⚠️ [防禦機制觸發] {data_id} FinMind API 無回應，自動跳過（原因：{e}）")
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


def _calc_rsi14(prices: pd.Series) -> float:
    if len(prices) < 15:
        return 50.0
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean().iloc[-1]
    avg_loss = loss.rolling(window=14).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 1)


def _calc_technical_score(close, ma5, ma10, ma30, rsi14) -> int:
    score = 0
    if ma5 > ma10 and ma10 > ma30:
        score += 15
    elif ma5 > ma30:
        score += 8
    elif close > ma30:
        score += 3
    if 50 <= rsi14 <= 70:
        score += 15
    elif 40 <= rsi14 < 50:
        score += 8
    elif rsi14 > 70:
        score += 5
    elif 30 <= rsi14 < 40:
        score += 2
    gap = (close - ma5) / ma5 * 100 if ma5 > 0 else 0
    if gap >= 3:
        score += 10
    elif gap >= 1:
        score += 7
    elif gap >= 0:
        score += 4
    return min(score, 40)


def _calc_volume_score(vol_lots, vol_ratio) -> int:
    score = 0
    if vol_ratio >= 2.0:
        score += 15
    elif vol_ratio >= 1.5:
        score += 12
    elif vol_ratio >= 1.0:
        score += 8
    elif vol_ratio >= 0.7:
        score += 4
    if vol_lots >= 10000:
        score += 10
    elif vol_lots >= 5000:
        score += 8
    elif vol_lots >= 3000:
        score += 6
    elif vol_lots >= 2000:
        score += 4
    return min(score, 25)



# =====================================================================
# 🏷️ V8.6 題材標籤對應（Grace 規格，零 API 消耗）
# =====================================================================
_THEME_MAP = [
    (["半導體", "積體電路", "晶圓", "IC", "封測"], "🔬 半導體"),
    (["AI", "人工智慧", "伺服器", "雲端", "資料中心", "網路通訊"], "🤖 AI/雲端"),
    (["電動車", "電池", "儲能", "新能源"], "🚗 電動車/儲能"),
    (["被動元件", "電容", "電阻", "電感"], "🔩 被動元件"),
    (["面板", "顯示器", "光電"], "📺 面板/光電"),
    (["生技", "醫療", "製藥", "醫材"], "💊 生技醫療"),
    (["金融", "銀行", "保險", "證券"], "🏦 金融"),
    (["航運", "海運", "空運"], "🚢 航運"),
    (["鋼鐵", "金屬", "原物料"], "🏗️ 原物料"),
    (["軟體", "資訊服務", "遊戲"], "💻 軟體/遊戲"),
    (["ETF", "指數"], "📊 ETF"),
]

def _get_theme_tag(industry: str) -> str:
    """V8.6：依產業類別對應題材標籤（Grace 規格）"""
    if not industry:
        return "📌 其他"
    for keywords, tag in _THEME_MAP:
        for kw in keywords:
            if kw.lower() in industry.lower():
                return tag
    return "📌 其他"

def _calc_chip_score(inst_buy, foreign_buy, trust_buy) -> int:
    score = 0
    if foreign_buy > 0 and trust_buy > 0:
        score += 15
    elif trust_buy > 0:
        score += 10
    elif foreign_buy > 0:
        score += 7
    if inst_buy >= 5000:
        score += 20
    elif inst_buy >= 1000:
        score += 15
    elif inst_buy >= 500:
        score += 10
    elif inst_buy > 0:
        score += 5
    return min(score, 35)


# =====================================================================
# 🆕 V8.6 Grace 題材標籤對應表（零 API 消耗）
# =====================================================================
_THEME_MAP = [
    (["半導體", "積體電路", "晶圓", "IC", "封測"], "🔬 半導體"),
    (["AI", "人工智慧", "伺服器", "雲端", "資料中心", "網路通訊"], "🤖 AI/雲端"),
    (["電動車", "電池", "儲能", "新能源"], "🚗 電動車/儲能"),
    (["被動元件", "電容", "電阻", "電感"], "🔩 被動元件"),
    (["面板", "顯示器", "光電"], "📺 面板/光電"),
    (["生技", "醫療", "製藥", "醫材"], "💊 生技醫療"),
    (["金融", "銀行", "保險", "證券"], "🏦 金融"),
    (["航運", "海運", "空運"], "🚢 航運"),
    (["鋼鐵", "金屬", "原物料"], "🏗️ 原物料"),
    (["軟體", "資訊服務", "遊戲"], "💻 軟體/遊戲"),
    (["ETF", "指數"], "📊 ETF"),
]


def _get_theme_tag(industry: str) -> str:
    """V8.6 Grace：由 industry_category 對應題材標籤（不消耗 API）"""
    if not industry:
        return "📌 其他"
    for keywords, tag in _THEME_MAP:
        for kw in keywords:
            if kw.lower() in industry.lower():
                return tag
    return "📌 其他"


def calculate_stock_data(sid, name, industry, df_prices, df_inst, force_show=False):
    try:
        if df_prices is not None and not df_prices.empty:
            if 'Close' not in df_prices.columns:
                df_prices = normalize_finmind_price_df(df_prices)

        if df_prices is None or df_prices.empty or len(df_prices) < 2:
            if force_show:
                return {
                    "stock_id": sid, "stock_name": name, "industry": industry,
                    "close": "無資料", "volume": 0, "inst_buy": 0,
                    "foreign_buy": 0, "trust_buy": 0, "ma5": 0, "ma30": 0,
                    "action": "靜候觀察", "target_price": 0, "stop_loss": 0,
                    "ma10": 0, "rsi14": 50.0, "vol_ratio": 1.0, "bull_align": False,
                    "chip_signal": "無買", "inst_grade": "X", "strength_score": 0,
                    "first_target": 0, "sweet_buy_low": 0, "sweet_buy_high": 0,
                    "theme_tag": _get_theme_tag(industry),
                }
            return None

        df_prices = df_prices.dropna(subset=['Close', 'Volume'])
        if df_prices.empty:
            return None

        latest = df_prices.iloc[-1]
        close_price = round(float(latest['Close']), 2)
        ma5 = round(float(df_prices['Close'].rolling(window=5).mean().iloc[-1]), 2) if len(df_prices) >= 5 else close_price
        ma30 = round(float(df_prices['Close'].rolling(window=30).mean().iloc[-1]), 2) if len(df_prices) >= 30 else close_price
        vol_lots = int(float(latest['Volume']) / 1000) if pd.notna(latest['Volume']) else 0

        # V8.5 新增技術指標（零 API 消耗，由 yfinance 資料計算）
        ma10 = round(float(df_prices['Close'].rolling(window=10).mean().iloc[-1]), 2) if len(df_prices) >= 10 else ma5
        vol_ma5 = df_prices['Volume'].rolling(window=5).mean().iloc[-1]
        vol_ratio = round(float(latest['Volume']) / float(vol_ma5), 2) if (pd.notna(vol_ma5) and vol_ma5 > 0) else 1.0
        rsi14 = _calc_rsi14(df_prices['Close'])
        bull_align = bool(ma5 > ma10 and ma10 > ma30)

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

        # V8.5 籌碼分級標籤
        chip_signal = (
            "雙買" if foreign_buy_30d > 0 and trust_buy_30d > 0
            else "投信單買" if trust_buy_30d > 0
            else "外資單買" if foreign_buy_30d > 0
            else "無買"
        )
        inst_grade = (
            "S" if inst_buy_30d >= 5000
            else "A" if inst_buy_30d >= 1000
            else "B" if inst_buy_30d >= 500
            else "C" if inst_buy_30d > 0
            else "X"
        )

        # V8.5 強勢評分（0-100，技術40 + 量能25 + 籌碼35）
        strength_score = (
            _calc_technical_score(close_price, ma5, ma10, ma30, rsi14)
            + _calc_volume_score(vol_lots, vol_ratio)
            + _calc_chip_score(inst_buy_30d, foreign_buy_30d, trust_buy_30d)
        )

        # 🆕 V8.6 Joe 甜蜜買進區間 & 第一停利
        ma_top = max(ma5, ma10)
        sweet_buy_low  = round(ma_top * 0.990, 2)
        sweet_buy_high = round(ma_top * 1.005, 2)
        first_target   = round(close_price * 1.15, 2)

        # 🆕 V8.6 Grace 題材標籤
        theme_tag = _get_theme_tag(industry)

        action = "買入加碼" if close_price >= ma5 and inst_buy_30d > 0 else "靜候觀察"

        # V8.6 甜蜜買進區間（Joe 計算法：MA5/MA10 上緣 -1% ~ +0.5%）
        ma_top = max(ma5, ma10)
        sweet_buy_low  = round(ma_top * 0.990, 2)
        sweet_buy_high = round(ma_top * 1.005, 2)
        # V8.6 第一停利（+15%）& 最終目標（+50%，沿用）
        first_target = round(close_price * 1.15, 2)
        # V8.6 題材標籤（Grace 規格）
        theme_tag = _get_theme_tag(industry)

        return {
            "stock_id": sid, "stock_name": name, "industry": industry,
            "close": close_price, "volume": vol_lots,
            "inst_buy": inst_buy_30d, "foreign_buy": foreign_buy_30d, "trust_buy": trust_buy_30d,
            "ma5": ma5, "ma30": ma30, "action": action,
            "target_price": round(close_price * 1.5, 2),
            "stop_loss": round(close_price * 0.9, 2),
            "first_target": first_target,
            "sweet_buy_low": sweet_buy_low,
            "sweet_buy_high": sweet_buy_high,
            "theme_tag": theme_tag,
            "ma10": ma10,
            "rsi14": rsi14,
            "vol_ratio": vol_ratio,
            "bull_align": bull_align,
            "chip_signal": chip_signal,
            "inst_grade": inst_grade,
            "strength_score": strength_score,
            "first_target": first_target,
            "sweet_buy_low": sweet_buy_low,
            "sweet_buy_high": sweet_buy_high,
            "theme_tag": theme_tag,
        }
    except Exception:
        if force_show:
            return {
                "stock_id": sid, "stock_name": name, "industry": industry,
                "close": "計算異常", "volume": 0, "inst_buy": 0,
                "foreign_buy": 0, "trust_buy": 0, "ma5": 0, "ma30": 0,
                "action": "靜候觀察", "target_price": 0, "stop_loss": 0,
                "ma10": 0, "rsi14": 50.0, "vol_ratio": 1.0, "bull_align": False,
                "chip_signal": "無買", "inst_grade": "X", "strength_score": 0,
                "first_target": 0, "sweet_buy_low": 0, "sweet_buy_high": 0,
                "theme_tag": _get_theme_tag(industry),
            }
        return None


def main():
    global _finmind_cache, _api_calls_count, _cache_hits_count, _stocks_processed_count

    # 讀取手動強制執行標籤
    force_run_flag = os.environ.get("FORCE_RUN") == "true"

    # 🆕 V7.9：例假日檢查（台灣時間，週六=5、週日=6 自動跳出）
    _check_time = datetime.utcnow() + timedelta(hours=8)
    if _check_time.weekday() >= 5:
        day_name = "週六" if _check_time.weekday() == 5 else "週日"
        if force_run_flag:
            print(f"⚠️ [例外狀況] 今日為 {day_name}（{_check_time.strftime('%Y-%m-%d')}），但偵測到指揮官強制執行指令，系統繞過休市檢查。")
            # 繼續往下執行，不 return
        else:
            print(f"📅 今日為 {day_name}（{_check_time.strftime('%Y-%m-%d')}），例假日不執行，Radar 休息。")
            _write_log_report(_check_time, status="Skipped-Holiday")
            return

    print("🌊 啟動彼夫有責戰情室 (V8.6 選股法則版：theme_tag + 甜蜜點 + 第一停利 + 籌碼分級 + 汪洋排序)...")

    # ── 載入本地快取（含 TTL 清理） ─────────────────────────────────────
    # 🆕 V7.8：啟動時自動清除超過 CACHE_TTL_HOURS 的過期資料
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                raw_cache = json.load(f)
            cutoff = datetime.utcnow() - timedelta(hours=CACHE_TTL_HOURS)
            cleaned = {}
            for k, v in raw_cache.items():
                if isinstance(v, dict) and "ts" in v:
                    try:
                        if datetime.fromisoformat(v["ts"]) >= cutoff:
                            cleaned[k] = v
                    except Exception:
                        pass
                elif isinstance(v, list):
                    cleaned[k] = v  # 舊格式：保留，下次命中時自動升級格式
            _finmind_cache = cleaned
            expired = len(raw_cache) - len(cleaned)
            print(f"  - 📦 快取載入：{len(cleaned)} 筆有效（清除 {expired} 筆過期 >24h）")
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
    # 🎯 Yahoo Finance 全市場粗篩段
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
    # =====================================================================
    market_pool = []
    added_market_sids = set()
    yf_skipped_ma5 = 0
    yf_passed_filter = 0

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

            # 第一關：量能門檻（V8.5 縮圈戰術，2000張）
            if vol_lots_yf < 2000:
                continue

            # 第二關：收盤 > MA30（趨勢確認）
            ma30_yf = float(df_yf['Close'].rolling(window=30).mean().iloc[-1])
            if close_yf <= ma30_yf:
                continue

            # 第三關：收盤 >= MA5（action 前置預判）
            ma5_yf = float(df_yf['Close'].rolling(window=5).mean().iloc[-1]) if len(df_yf) >= 5 else close_yf
            if close_yf < ma5_yf:
                yf_skipped_ma5 += 1
                continue

            yf_passed_filter += 1
            df_i = fetch_finmind("TaiwanStockInstitutionalInvestorsBuySell", start_30d, today_str, sid)
            time.sleep(0.2)

            ind = industry_map.get(sid, "未知產業")
            s_data = calculate_stock_data(sid, name_map.get(sid, sid), ind, df_yf, df_i)
            if s_data and s_data['action'] == "買入加碼":
                market_pool.append(s_data)
                added_market_sids.add(sid)
        except Exception:
            continue

    print(f"  - 📊 MA5 預篩：攔截 {yf_skipped_ma5} 支（必靜候），{yf_passed_filter} 支進入籌碼精篩")

    # V8.5：汪洋大魚依強勢評分由高到低排序
    market_pool.sort(key=lambda x: x.get('strength_score', 0), reverse=True)

    # 🎯 V7 核心升級：Date-Lock 日期防呆機制與向下相容
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

    print(f"  - 🔥 姊夫魚池：{POOL_SETTINGS['🔥 姊夫爆發小魚池']}")

    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)

    # =====================================================================
    # 🎯 V7.5 魚池監控段
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

            df_price_to_use = valid_dfs.get(sid)
            if df_price_to_use is None or df_price_to_use.empty:
                print(f"      - Yahoo 未命中，啟動 {sid} 雙重火力補抓（Yahoo 備援）...")
                df_price_to_use = download_yf_data_single(sid, market_map)
                if df_price_to_use is None or df_price_to_use.empty:
                    print(f"      - Yahoo 備援失敗，改用 FinMind 股價（{sid}）...")
                    df_price_to_use = fetch_finmind("TaiwanStockPrice", start_60d, today_str, sid)

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
    # 🎯 V7.6 前端儀表板數據預計算
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

    _save_cache_to_disk()
    print(f"  - 💾 快取最終寫盤完成，共 {len(_finmind_cache)} 筆（下次執行可直接命中）")

    _stocks_processed_count = sum(len(v) for v in final_data_structure.values())

    _write_log_report(taiwan_time, stocks_processed=_stocks_processed_count, status="Success")

    print(f"\n🎉 掃描完成！本次共消耗 FinMind API {_api_calls_count} 次（快取命中 {_cache_hits_count} 次）")
    print(f"   V8.6 儀表板數據：產業 {len(industry_dist)} 類、魚池多空 {buy_n}/{watch_n}、處理 {_stocks_processed_count} 檔")

    # 🆕 V7.9：本地執行時自動呼叫 git_sync.py 推送戰報
    if not os.environ.get("GITHUB_ACTIONS"):
        push_status = "OK"
        try:
            git_sync_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "git_sync.py")
            result = subprocess.run([sys.executable, git_sync_path], check=False, timeout=120)
            if result.returncode != 0:
                push_status = "FAILED"
                print(f"  ⚠️ git_sync.py 結束碼：{result.returncode}，請手動確認推送")
        except subprocess.TimeoutExpired:
            push_status = "TIMEOUT"
            print("  ⚠️ git_sync.py 超過 120 秒未完成，可能為網路異常，請手動執行推送")
        except Exception as e:
            push_status = "ERROR"
            print(f"  ⚠️ git_sync.py 呼叫失敗（不影響本次結果）：{e}")
        if push_status != "OK":
            try:
                with open(LOG_REPORT_FILE, 'r', encoding='utf-8') as f:
                    _log = json.load(f)
                _log["push_status"] = push_status
                with open(LOG_REPORT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(_log, f, ensure_ascii=False, indent=2)
            except Exception:
                pass


if __name__ == "__main__":
    main()
