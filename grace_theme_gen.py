# ==========================================
# Grace 題材分析產生器 V1.0（任務4）— 被動元件
# ==========================================
# 仿孟恭範式：規則式本機產生，零外部 API。
# 讀 plum_blossom_data.json 的「🃏 被動卡娃魚池」量化欄位，
# 套 Grace SKILL 分析框架 → 產出 grace_theme_data.json。
# 每日由 grace_run.py 觸發更新（台灣時間 06:00）。
# ==========================================
import sys, io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import json
from datetime import datetime, timezone, timedelta

TW_TZ = timezone(timedelta(hours=8))
PLUM_FILE = "plum_blossom_data.json"
OUTPUT_FILE = "grace_theme_data.json"
PASSIVE_POOL = "🃏 被動卡娃魚池"

# 被動元件子類對應（題材類型）
SUBCAT = {
    "6173": "MLCC・陶瓷電容", "3026": "MLCC・陶瓷電容", "2492": "MLCC・晶片電阻",
    "6175": "鋁質電容", "2472": "鋁質電解電容", "2327": "被動元件龍頭（MLCC）",
    "2375": "鋁質電容", "6449": "固態電容", "8042": "電感",
    "8163": "被動模組", "3090": "被動元件通路", "3537": "電感・被動", "6432": "電感",
}

# 被動元件題材庫（依子類給對應產業催化劑）
def _sector_catalyst(subcat: str) -> str:
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


def main():
    now_tw = datetime.now(TW_TZ)
    print("🎯 Grace 題材分析產生器 V1.0（被動元件）啟動...")
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

    tiers = {"Tier 1": [], "Tier 2": [], "Tier 3": []}
    src_date = ""
    for s in passive:
        sid = str(s.get("stock_id", ""))
        subcat = SUBCAT.get(sid, "被動元件")
        level, level_note = _sustainability(s)
        src_date = s.get("price_date", src_date)
        card = {
            "stock_id": sid,
            "stock_name": s.get("stock_name", sid),
            "theme_type": f"被動元件 ─ {subcat}",
            "catalyst": _build_catalyst(s, subcat),
            "sustainability_level": level,
            "sustainability_note": level_note,
            "risk": _build_risk(s),
            # 量化快照（供前端佐證）
            "close": s.get("close", 0),
            "strength_score": s.get("strength_score", 0),
            "chip_signal": s.get("chip_signal", "無買"),
            "inst_grade": s.get("inst_grade", "X"),
            "rsi14": s.get("rsi14", 50),
            "vol_ratio": s.get("vol_ratio", 1.0),
            "action": s.get("action", "靜候觀察"),
        }
        tier = s.get("tier", "Tier 3")
        tiers.setdefault(tier, []).append(card)

    # 題材總覽：依各檔持續性統計
    all_cards = [c for v in tiers.values() for c in v]
    high_n = sum(1 for c in all_cards if c["sustainability_level"] == "高")
    mid_n = sum(1 for c in all_cards if c["sustainability_level"] == "中")
    low_n = sum(1 for c in all_cards if c["sustainability_level"] == "低")
    overview = (
        f"被動元件族群本週題材聚焦 AI 伺服器高階 MLCC、車用電子含量提升與庫存回補循環。"
        f"觀察名單 {len(all_cards)} 檔中，題材持續性評為高 {high_n} 檔、中 {mid_n} 檔、低 {low_n} 檔。"
        f"操作上以法人雙買且動能轉強者優先，超買與量縮個股宜耐心等待回測。"
    )

    report = {
        "last_updated": now_tw.strftime("%Y-%m-%d %H:%M（自動排程）"),
        "analyst": "Grace（題材面研究員）",
        "theme": "被動元件",
        "source_price_date": src_date,
        "theme_overview": overview,
        "stat": {"high": high_n, "mid": mid_n, "low": low_n, "total": len(all_cards)},
        "tiers": tiers,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"✅ 已輸出 {OUTPUT_FILE}（{len(all_cards)} 檔；高{high_n}/中{mid_n}/低{low_n}）")


if __name__ == "__main__":
    main()
