# ==========================================
# Grace 題材分析產生器 V2.0 — 多題材＋題材鏈（V9.7）
# ==========================================
# 仿孟恭範式：規則式本機產生，零外部 API。
# 讀 plum_blossom_data.json 的「🃏 被動卡娃魚池」與 V9.7 頂層 theme_watch（六大題材），
# 套 Grace SKILL 分析框架 → 產出 grace_theme_data.json。
# 每日由 grace_run.py 觸發更新（台灣時間 06:00）。
#
# V2.0（2026-10-19）：
#   ① 題材由「被動元件」單一題材擴為 7 大題材（被動元件＋CCL/PCB/玻纖布/樹脂、記憶體/HDD、
#      封測、散熱/電源、資安/軟體、特用化學）
#   ② 題材熱度：站上 MA5 比例（廣度）、近 5 日平均報酬、平均強勢評分 → 升溫／盤整／降溫
#   ③ 題材連動：近 20 日題材等權日報酬的 Pearson 相關；門檻隨當日共同漲跌程度自適應 ——
#      ρ ≥ max(LINK_THRESHOLD, 全題材兩兩平均 ρ ＋ LINK_MARGIN)，且雙方皆非降溫即相連；
#      連通且含升溫題材的群組 = 主題鏈（前端置頂）。
#      不採「扣除全題材平均」的殘差相關：只有 7 個題材時殘差相關系統性偏負（約 −1/6），
#      2026-10-19 實測最高僅 0.32，鏈幾乎不可能成立
#   ④ 舊欄位（tiers／stat／theme_overview）保留，舊版 grace.html 仍可讀
# ==========================================
import sys, io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import json
import hashlib
from datetime import datetime, timezone, timedelta

TW_TZ = timezone(timedelta(hours=8))
PLUM_FILE = "plum_blossom_data.json"
OUTPUT_FILE = "grace_theme_data.json"
PASSIVE_POOL = "🃏 被動卡娃魚池"
PASSIVE_THEME = "被動元件"

LINK_THRESHOLD = 0.6      # 相關係數絕對下限
LINK_MARGIN = 0.15        # 須高於當日全題材兩兩平均相關的幅度（大盤齊漲齊跌時自動拉高門檻）
MIN_LINK_POINTS = 10      # 相關係數至少需要的日報酬筆數

# 供應鏈順序（上游材料 → 元件 → 封測 → 系統 → 應用），主題鏈內依此排列
CHAIN_ORDER = ["特用化學", "CCL/PCB/玻纖布/樹脂", PASSIVE_THEME, "記憶體/HDD",
               "封測", "散熱/電源", "資安/軟體"]

# 被動元件子類對應（題材類型）
SUBCAT = {
    "6173": "MLCC・陶瓷電容", "3026": "MLCC・陶瓷電容", "2492": "MLCC・晶片電阻",
    "6175": "鋁質電容", "2472": "鋁質電解電容", "2327": "被動元件龍頭（MLCC）",
    "2375": "鋁質電容", "6449": "固態電容", "8042": "電感",
    "8163": "被動模組", "3090": "被動元件通路", "3537": "電感・被動", "6432": "電感",
}
TIER_LABEL = {"Tier 1": "Tier 1 核心", "Tier 2": "Tier 2 主力", "Tier 3": "Tier 3 衛星"}

# 新題材子類的產業背景（規則式題材敘述，非即時新聞）
SUBCAT_CATALYST = {
    "CCL 銅箔基板": "AI 伺服器與高速交換器推升 M7 以上高階 CCL 用量，產能利用率高、具議價能力",
    "PCB 載板": "AI 加速卡與 ABF 載板層數、面積提升，高階 PCB 產能吃緊",
    "玻纖布": "Low-Dk 高階玻纖布供給吃緊，日系大廠漲價、台廠擴產與認證進度為焦點",
    "高頻樹脂": "高頻高速 CCL 帶動低介電樹脂需求，材料認證進度決定放量時點",
    "記憶體": "AI 伺服器與 HBM 排擠一般型 DRAM／NAND 產能，報價循環與庫存回補為主軸",
    "HDD 零組件": "雲端近線儲存需求強，HDD 原廠產能吃緊，零組件拉貨動能延續",
    "封裝": "CoWoS 等先進封裝產能外溢，AI 晶片封裝需求帶動稼動率",
    "測試": "AI 晶片測試時間拉長、測試機台需求提升，測試廠稼動率走高",
    "散熱": "AI 伺服器功耗攀升，水冷板／液冷方案滲透率提升",
    "電源": "高瓦數伺服器電源與 BBU 需求擴大，資料中心電力架構升級",
    "資安": "企業與政府資安法遵、AI 應用擴大攻擊面，資安支出維持成長",
    "軟體服務": "企業 AI 導入與雲端轉型帶動系統整合與軟體服務需求",
    "半導體特化": "先進製程推升高純度電子化學品規格，在地化供應鏈受惠",
    "電子材料": "先進封裝與顯示材料規格升級，特用材料打入新應用",
}


def _sector_catalyst(subcat: str) -> str:
    if subcat in SUBCAT_CATALYST:
        return SUBCAT_CATALYST[subcat]
    if "MLCC" in subcat or "陶瓷" in subcat or "晶片電阻" in subcat:
        return "AI 伺服器與資料中心帶動高階 MLCC 需求，疊加 MLCC 漲價循環與庫存回補"
    if "電容" in subcat:
        return "車用電子與工控需求回溫，電容急單與旺季拉貨題材發酵"
    if "電感" in subcat:
        return "AI 伺服器電源與車用電子推升電感用量，高階產品供不應求"
    if "通路" in subcat:
        return "被動元件通路庫存去化完成，下游急單帶動拉貨動能"
    return "被動元件景氣回溫，庫存回補與旺季拉貨題材延續"


def _chip_phrase(chip_signal: str) -> str:
    return {
        "雙買": "外資投信同步進駐",
        "投信單買": "投信買盤點火",
        "外資單買": "外資資金回補",
        "無買": "法人態度中性、待籌碼轉強",
    }.get(chip_signal, "法人動向待觀察")


def _momentum_phrase(score: int) -> str:
    if score >= 60:
        return "動能強勁"
    if score >= 40:
        return "動能溫和增溫"
    return "動能待轉強"


def _build_catalyst(s: dict, subcat: str) -> str:
    sector = _sector_catalyst(subcat)
    chip = _chip_phrase(s.get("chip_signal", "無買"))
    mom = _momentum_phrase(s.get("strength_score", 0))
    return f"{sector}；{chip}，{mom}（強勢評分 {s.get('strength_score', 0)}）。"


def _sustainability(s: dict):
    score = s.get("strength_score", 0)
    trend = s.get("trend_quality", "N/A")
    grade = s.get("inst_grade", "X")
    if score >= 60 and trend in ("STRONG", "HEALTHY") and grade in ("S", "A"):
        return "高", "量價籌碼三線同步轉強，題材續航力佳"
    if score >= 40 or trend == "WATCH":
        return "中", "動能與籌碼初步成形，需待量能進一步確認"
    return "低", "題材尚未獲量價籌碼共振，宜列觀察"


def _build_risk(s: dict) -> str:
    risks = []
    rsi = s.get("rsi14", 50)
    vr = s.get("vol_ratio", 1.0)
    close = s.get("close", 0)
    ma5 = s.get("ma5", 0)
    if s.get("data_note"):
        risks.append(str(s["data_note"]))
    if isinstance(rsi, (int, float)) and rsi > 70:
        risks.append(f"RSI {rsi} 進入超買區，留意短線過熱回檔")
    if isinstance(vr, (int, float)) and vr < 0.7:
        risks.append(f"量比 {vr} 量能偏弱，缺乏資金續攻力道")
    if s.get("foreign_buy", 0) < 0 or s.get("trust_buy", 0) < 0:
        risks.append("法人出現調節賣壓，籌碼面鬆動")
    if isinstance(close, (int, float)) and isinstance(ma5, (int, float)) and ma5 > 0:
        dev = (close / ma5 - 1) * 100
        if dev > 8:
            risks.append(f"股價乖離 5 日線達 {round(dev, 1)}%，追高風險升高")
    if not risks:
        return "目前無明顯風險訊號，緊盯量能與法人動向即可。"
    return "；".join(risks) + "。"


def _is_plum_usable(passive: list) -> tuple:
    """
    🛡️ V1.1：判斷來源戰報的卡片是否為有效資料。

    radar.py 在全市場下載失敗時，會以 force_show 產出佔位卡片
    （close="無資料"、price_date="0000-00-00"、strength_score=0），
    這種戰報不可用於題材分析。回傳 (可用與否, 原因)。
    """
    bad_date = sum(1 for s in passive if str(s.get("price_date", "")) in ("", "0000-00-00"))
    if bad_date == len(passive):
        return False, "全數個股 price_date 為 0000-00-00"
    no_close = sum(1 for s in passive if not isinstance(s.get("close"), (int, float)))
    if no_close == len(passive):
        return False, "全數個股 close 為「無資料」"
    return True, ""


def _make_card(s: dict, subcat: str, theme: str) -> dict:
    level, level_note = _sustainability(s)
    return {
        "stock_id": str(s.get("stock_id", "")),
        "stock_name": s.get("stock_name", s.get("stock_id", "")),
        "theme_type": f"{theme} ─ {subcat}",
        "subcat": subcat,
        "catalyst": _build_catalyst(s, subcat),
        "sustainability_level": level,
        "sustainability_note": level_note,
        "risk": _build_risk(s),
        # 量化快照（供前端佐證）
        "close": s.get("close", 0),
        "ma5": s.get("ma5", 0),
        "strength_score": s.get("strength_score", 0),
        "chip_signal": s.get("chip_signal", "無買"),
        "inst_grade": s.get("inst_grade", "X"),
        "rsi14": s.get("rsi14", 50),
        "vol_ratio": s.get("vol_ratio", 1.0),
        "action": s.get("action", "靜候觀察"),
        "ret_5d": _ret(s.get("closes_21d") or [], 5),
    }


# ─────────────────────────── 題材熱度與連動（純函式，供 tests 斷言） ───────────────────────────
def _ret(closes: list, n: int):
    """近 n 日報酬（%）；資料不足回傳 None。"""
    if len(closes) <= n or not closes[-1 - n]:
        return None
    return round((closes[-1] / closes[-1 - n] - 1) * 100, 2)


def _daily_returns(closes: list) -> list:
    return [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes)) if closes[i - 1]]


def _theme_index_returns(stocks: list, n_days: int = 20) -> list:
    """題材等權日報酬：取各股近 n_days 筆日報酬，依尾端對齊後逐日平均；不足 n_days 筆的個股不納入。"""
    series = []
    for s in stocks:
        closes = [c for c in (s.get("closes_21d") or []) if isinstance(c, (int, float))]
        r = _daily_returns(closes)
        if len(r) >= n_days:
            series.append(r[-n_days:])
    if not series:
        return []
    return [sum(col) / len(col) for col in zip(*series)]


def _pearson(a: list, b: list):
    n = min(len(a), len(b))
    if n < MIN_LINK_POINTS:
        return None
    a, b = a[-n:], b[-n:]
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va == 0 or vb == 0:
        return None
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return round(cov / (va * vb) ** 0.5, 3)


def _theme_heat(stocks: list) -> dict:
    """
    題材熱度。廣度＝收盤 ≥ MA5 的比例；ret_5d＝成分股近 5 日報酬平均。
      升溫：廣度 ≥ 60% 且 ret_5d > 0
      降溫：廣度 ≤ 30% 且 ret_5d < 0
      其餘：盤整（含資料不足）
    heat（0～100 參考分）＝廣度 50% ＋ 平均評分 30% ＋ 5 日報酬（±10% 截斷）20%
    """
    valid = [s for s in stocks
             if isinstance(s.get("close"), (int, float)) and isinstance(s.get("ma5"), (int, float))]
    total = len(stocks)
    if not valid:
        return {"status": "盤整", "heat": 0, "breadth": 0.0, "buy_n": 0, "total": total,
                "avg_score": 0, "ret_5d": None, "ret_20d": None}
    above = sum(1 for s in valid if s["ma5"] > 0 and s["close"] >= s["ma5"])
    breadth = above / len(valid)
    avg_score = sum(s.get("strength_score", 0) for s in valid) / len(valid)
    r5 = [x for x in (_ret(s.get("closes_21d") or [], 5) for s in valid) if x is not None]
    r20 = [x for x in (_ret(s.get("closes_21d") or [], 20) for s in valid) if x is not None]
    ret_5d = round(sum(r5) / len(r5), 2) if r5 else None
    ret_20d = round(sum(r20) / len(r20), 2) if r20 else None
    if ret_5d is not None and breadth >= 0.6 and ret_5d > 0:
        status = "升溫"
    elif ret_5d is not None and breadth <= 0.3 and ret_5d < 0:
        status = "降溫"
    else:
        status = "盤整"
    r5c = max(-10.0, min(10.0, ret_5d or 0.0))
    heat = round(breadth * 50 + avg_score * 0.3 + (r5c + 10) * 1.0)
    return {"status": status, "heat": max(0, min(100, heat)), "breadth": round(breadth, 3),
            "buy_n": sum(1 for s in valid if s.get("action") == "買入加碼"), "total": total,
            "avg_score": round(avg_score, 1), "ret_5d": ret_5d, "ret_20d": ret_20d}


def _correlation_matrix(index_returns: dict) -> dict:
    """各題材等權日報酬的 Pearson 相關矩陣（尾端對齊；筆數不足 MIN_LINK_POINTS 的題材不列入）。"""
    names = [k for k, v in index_returns.items() if len(v) >= MIN_LINK_POINTS]
    if len(names) < 2:
        return {"names": names, "matrix": [[None] * len(names) for _ in names]}
    n = min(len(index_returns[k]) for k in names)
    aligned = {k: index_returns[k][-n:] for k in names}
    matrix = [[1.0 if a == b else _pearson(aligned[a], aligned[b]) for b in names] for a in names]
    return {"names": names, "matrix": matrix}


def _link_threshold(corr: dict) -> tuple:
    """
    自適應連動門檻 = max(LINK_THRESHOLD, 全題材兩兩平均 ρ ＋ LINK_MARGIN)。
    大盤齊漲齊跌時兩兩相關普遍偏高，門檻跟著拉高，只留下「比大盤更同步」的題材對。
    回傳 (門檻, 兩兩平均 ρ 或 None)。
    """
    vals = [r for i, row in enumerate(corr["matrix"]) for j, r in enumerate(row) if j > i and r is not None]
    if not vals:
        return LINK_THRESHOLD, None
    mean = sum(vals) / len(vals)
    return round(max(LINK_THRESHOLD, mean + LINK_MARGIN), 3), round(mean, 3)


def _build_chains(heat: dict, corr: dict, threshold: float = LINK_THRESHOLD) -> list:
    """
    主題鏈：相關 ≥ threshold 且雙方皆非「降溫」即相連；連通群組 ≥ 2 個題材、且至少一個「升溫」才成鏈。
    鏈內依 CHAIN_ORDER（供應鏈上游→下游）排列；多條鏈依平均 heat 由高到低。
    """
    names, matrix = corr["names"], corr["matrix"]
    edges = []
    for i, a in enumerate(names):
        for j in range(i + 1, len(names)):
            b, r = names[j], matrix[i][j]
            if r is None or r < threshold:
                continue
            if heat.get(a, {}).get("status") == "降溫" or heat.get(b, {}).get("status") == "降溫":
                continue
            edges.append((a, b, r))
    parent = {k: k for k in names}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b, _ in edges:
        parent[find(a)] = find(b)
    groups = {}
    for k in names:
        groups.setdefault(find(k), []).append(k)

    order = {k: i for i, k in enumerate(CHAIN_ORDER)}
    chains = []
    for members in groups.values():
        if len(members) < 2 or not any(heat.get(m, {}).get("status") == "升溫" for m in members):
            continue
        members.sort(key=lambda m: order.get(m, 99))
        links = [{"a": a, "b": b, "corr": r} for a, b, r in edges if a in members and b in members]
        avg_heat = round(sum(heat[m]["heat"] for m in members) / len(members), 1)
        chains.append({"themes": members, "links": links, "heat": avg_heat})
    chains.sort(key=lambda c: -c["heat"])
    return chains


def _block_hash(prev_hash: str, name: str, src_date: str, heat: int) -> str:
    """區塊雜湊：串接前一區塊雜湊，任何一個題材熱度變動都會改變其後所有區塊雜湊（呈現用）。"""
    return hashlib.sha256(f"{prev_hash}|{name}|{src_date}|{heat}".encode("utf-8")).hexdigest()[:10]


def main():
    now_tw = datetime.now(TW_TZ)
    print("🎯 Grace 題材分析產生器 V2.0（多題材＋題材鏈）啟動...")
    try:
        with open(PLUM_FILE, "r", encoding="utf-8") as f:
            plum = json.load(f)
    except Exception as e:
        print(f"❌ 無法讀取 {PLUM_FILE}：{e}")
        return

    passive = plum.get("pools", {}).get(PASSIVE_POOL, [])
    if not passive:
        print("❌ plum 中無被動卡娃魚池資料，終止。")
        return

    # 🛡️ V1.1（2026-09-17 稽核）：拒吃壞戰報
    #    2026-09-16 radar 全市場下載整批失敗，仍產出全「無資料」戰報並推上線；
    #    隔日 06:00 本程式照吃，害 grace_theme_data.json 的 source_price_date
    #    變成 0000-00-00、13 檔持續性全評「低」，錯誤資料在站上掛了一整天。
    #    radar.py V9.4 已於上游加空跑保護，此處為第二道防線：
    #    來源戰報明顯無效時保留既有題材檔，不覆寫、不推送。
    ok_src, src_reason = _is_plum_usable(passive)
    if not ok_src:
        print(f"❌ 來源戰報無效（{src_reason}），保留既有 {OUTPUT_FILE} 不覆寫。")
        return

    # ── 被動元件（沿用 Tier 結構，舊欄位 tiers 保留）──
    tiers = {"Tier 1": [], "Tier 2": [], "Tier 3": []}
    src_date = ""
    for s in passive:
        sid = str(s.get("stock_id", ""))
        src_date = s.get("price_date", src_date)
        card = _make_card(s, SUBCAT.get(sid, "被動元件"), PASSIVE_THEME)
        tiers.setdefault(s.get("tier", "Tier 3"), []).append(card)

    # ── 題材原始資料（被動元件＋V9.7 theme_watch）──
    raw = {PASSIVE_THEME: {"icon": "🃏", "stocks": passive,
                           "group_of": lambda s: TIER_LABEL.get(s.get("tier", "Tier 3"), "Tier 3 衛星"),
                           "subcat_of": lambda s: SUBCAT.get(str(s.get("stock_id", "")), "被動元件")}}
    tw = plum.get("theme_watch") or {}
    for tname, tcfg in tw.items():
        stocks = tcfg.get("stocks", [])
        if not stocks or not _is_plum_usable(stocks)[0]:
            print(f"⚠️ 題材「{tname}」來源資料無效，本次略過。")
            continue
        raw[tname] = {"icon": tcfg.get("icon", "🔹"), "stocks": stocks,
                      "group_of": lambda s: s.get("subcat", "其他"),
                      "subcat_of": lambda s: s.get("subcat", "其他")}
    if not tw:
        print("ℹ️ 來源戰報尚無 theme_watch（radar.py < V9.7），僅產出被動元件題材。")

    heat = {k: _theme_heat(v["stocks"]) for k, v in raw.items()}
    idx_ret = {k: _theme_index_returns(v["stocks"]) for k, v in raw.items()}
    corr = _correlation_matrix(idx_ret)
    link_thr, mean_corr = _link_threshold(corr)
    chains = _build_chains(heat, corr, link_thr)

    # ── 題材區塊（依供應鏈順序，區塊雜湊逐一串接）──
    order = {k: i for i, k in enumerate(CHAIN_ORDER)}
    themes = []
    prev = "0" * 10
    for no, tname in enumerate(sorted(raw, key=lambda k: order.get(k, 99)), start=1):
        cfg = raw[tname]
        groups = {}
        for s in cfg["stocks"]:
            groups.setdefault(cfg["group_of"](s), []).append(_make_card(s, cfg["subcat_of"](s), tname))
        linked = []
        if tname in corr["names"]:
            i = corr["names"].index(tname)
            for j, other in enumerate(corr["names"]):
                r = corr["matrix"][i][j]
                if other != tname and r is not None and r >= link_thr:
                    linked.append({"theme": other, "corr": r})
            linked.sort(key=lambda x: -x["corr"])
        h = heat[tname]
        bh = _block_hash(prev, tname, src_date, h["heat"])
        themes.append({"block_no": no, "name": tname, "icon": cfg["icon"],
                       "hash": bh, "prev_hash": prev, **h,
                       "in_chain": any(tname in c["themes"] for c in chains),
                       "linked": linked, "groups": groups})
        prev = bh

    # ── 總覽（stat 統計全部題材卡片，同一檔跨題材只計一次）──
    uniq = {}
    for t in themes:
        for cards in t["groups"].values():
            for c in cards:
                uniq.setdefault(c["stock_id"], c)
    all_cards = list(uniq.values())
    high_n = sum(1 for c in all_cards if c["sustainability_level"] == "高")
    mid_n = sum(1 for c in all_cards if c["sustainability_level"] == "中")
    low_n = sum(1 for c in all_cards if c["sustainability_level"] == "低")
    warm = [t["name"] for t in themes if t["status"] == "升溫"]
    cool = [t["name"] for t in themes if t["status"] == "降溫"]
    chain_txt = ("；".join("→".join(c["themes"]) for c in chains)) if chains else "目前無題材形成連動鏈"
    overview = (
        f"本期追蹤 {len(themes)} 大題材、{len(all_cards)} 檔。"
        f"升溫：{('、'.join(warm)) or '無'}；降溫：{('、'.join(cool)) or '無'}。"
        f"主題鏈：{chain_txt}。"
        f"題材持續性評為高 {high_n} 檔、中 {mid_n} 檔、低 {low_n} 檔；"
        f"操作上以法人雙買且動能轉強者優先，超買與量縮個股宜耐心等待回測。"
    )

    report = {
        "version": "V2.0",
        "last_updated": now_tw.strftime("%Y-%m-%d %H:%M（自動排程）"),
        "analyst": "Grace（題材面研究員）",
        "theme": "多題材（被動元件＋六大題材）",
        "source_price_date": src_date,
        "theme_overview": overview,
        "stat": {"high": high_n, "mid": mid_n, "low": low_n, "total": len(all_cards)},
        "tiers": tiers,
        "themes": themes,
        "chains": chains,
        "correlation": corr,
        "link_threshold": link_thr,
        "mean_corr": mean_corr,
        "linkage_basis": (f"近 20 日題材等權日報酬 Pearson 相關；門檻＝max({LINK_THRESHOLD}，"
                          f"兩兩平均 ρ {mean_corr} ＋ {LINK_MARGIN})"),
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"✅ 已輸出 {OUTPUT_FILE}（{len(themes)} 題材／{len(all_cards)} 檔；"
          f"高{high_n}/中{mid_n}/低{low_n}；主題鏈 {len(chains)} 條）")


if __name__ == "__main__":
    main()
