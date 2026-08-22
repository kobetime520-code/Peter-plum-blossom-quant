"""
tests/test_gates.py — V9.x 選股閘門離線回歸測試（稽核 D3）

性質：純離線。不呼叫 FinMind、不連 yfinance、不讀寫戰報檔、不推送。
執行：python tests/run_all.py     （或 python tests/test_gates.py）

涵蓋範圍（皆為 V9.0～V9.2 新增、原本毫無自動化保護的邏輯）：
  ① A1 籌碼方向閘門 ＋ A2 追高防護     _passes_ocean_gates
  ② 記憶海真·僅追加 ＋ 防縮水護欄      merge_ocean_history
  ③ 姊夫池貴金屬 ETF 固定名單          JIEFU_ETF_POOL / JIEFU_ETF_PARAMS（V9.3）
  ④ 姊夫池分級停損停利與建議部位       _apply_jiefu_risk_params（V9.3）
  ⑤ 姊夫池 ETF 技術訊號與方向標註      _apply_jiefu_etf_signal（V9.3）
  ⑥ 大盤環境三段式與 rsi_ceiling       _calc_market_regime（以假資料替換 yfinance）
"""
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import radar

_checks = 0


def ok(cond, msg):
    global _checks
    _checks += 1
    if not cond:
        raise AssertionError(msg)
    print(f"  ✅ {msg}")


def section(title):
    print(f"\n── {title} " + "─" * max(0, 56 - len(title)))


# =====================================================================
# ① A1 籌碼方向閘門 ＋ A2 追高防護
# =====================================================================
def _stock(foreign=0, trust=0, rsi=50):
    return {"foreign_buy": foreign, "trust_buy": trust, "rsi14": rsi}


def test_ocean_gates():
    section("① A1 籌碼方向閘門 ＋ A2 追高防護")
    g = radar._passes_ocean_gates

    ok(g(_stock(foreign=500, trust=300), 80) == (True, ""), "外資投信雙買且 RSI 低於上限 → 通過")
    ok(g(_stock(foreign=500, trust=0), 80) == (True, ""), "外資單買 → 通過")
    ok(g(_stock(foreign=0, trust=500), 80) == (True, ""), "投信單買 → 通過")

    # A1 的核心價值：合計淨買超為正、但外資投信皆非買方（自營商撐起的「假合計正」）
    ok(g(_stock(foreign=0, trust=0), 80) == (False, "chip"), "外資投信皆未買（假合計正）→ A1 攔截")
    ok(g(_stock(foreign=-800, trust=-200), 80) == (False, "chip"), "外資投信雙賣 → A1 攔截")

    # A2 為 >=，恰好等於上限也要攔
    ok(g(_stock(foreign=500, rsi=80), 80) == (False, "rsi"), "RSI 等於上限 80 → A2 攔截（邊界）")
    ok(g(_stock(foreign=500, rsi=79.9), 80) == (True, ""), "RSI 79.9 低於上限 80 → 通過（邊界）")
    ok(g(_stock(foreign=500, rsi=72), 70) == (False, "rsi"), "空頭上限 70 下，RSI 72 → A2 攔截")
    ok(g(_stock(foreign=500, rsi=72), 80) == (True, ""), "同一支股票在多頭上限 80 下 → 通過（上限確實生效）")

    # 兩道閘門的先後：籌碼不合格時先被 A1 擋下，不應回報 rsi
    ok(g(_stock(foreign=0, trust=0, rsi=95), 80) == (False, "chip"), "籌碼與 RSI 同時不合格 → 歸因 A1（順序）")


# =====================================================================
# ② 記憶海真·僅追加 ＋ 防縮水護欄
# =====================================================================
def test_merge_ocean_history():
    section("② 記憶海真·僅追加 ＋ 防縮水護欄")
    m = radar.merge_ocean_history
    TODAY = "2026-08-01"

    # 核心：當日未命中者原樣保留 —— 舊版整檔覆寫的 bug（F-01）就死在這一條
    hist = {
        "1101": {"count": 5, "last_date": "2026-07-30"},
        "2330": {"count": 2, "last_date": "2026-07-31"},
    }
    new, promoted, guard = m(hist, ["2330"], TODAY)
    ok(len(new) == 2, "當日只命中 1 支，記憶海仍保有 2 筆（未命中者原樣保留）")
    ok(new["1101"] == {"count": 5, "last_date": "2026-07-30"}, "未命中股 1101 的 count/last_date 完全不變")
    ok(new["2330"]["count"] == 3 and new["2330"]["last_date"] == TODAY, "命中股 2330 累計 2→3 且日期更新")
    ok(promoted == ["2330"], "2330 達 count≥3 → 列入猛虎晉升")
    ok(guard is None, "正常情況無護欄觸發")

    # 同日重跑（補跑情境）不得重複累加
    new2, _, _ = m(new, ["2330"], TODAY)
    ok(new2["2330"]["count"] == 3, "同日重跑 2330 維持 3，不重複累加（Date-Lock）")

    # 新股票首次出現
    new3, promoted3, _ = m(hist, ["6173"], TODAY)
    ok(new3["6173"] == {"count": 1, "last_date": TODAY}, "首次出現的 6173 記為 count=1")
    ok(promoted3 == [], "count=1 不晉升猛虎")
    ok(len(new3) == 3, "新股票為追加，不取代既有 2 筆")

    # 向下相容：V6 以前為純 int
    new4, _, _ = m({"1101": 4, "2330": 1}, ["1101"], TODAY)
    ok(new4["1101"] == {"count": 5, "last_date": TODAY}, "V6 純 int 格式的命中股正確轉換並累加")
    ok(new4["2330"] == {"count": 1, "last_date": ""}, "V6 純 int 格式的未命中股也完成正規化（整份生效）")

    # 空手日：0 支命中時保留既有累計
    new5, promoted5, guard5 = m(hist, [], TODAY)
    ok(new5 == hist and promoted5 == [], "汪洋 0 支 → 記憶海原樣保留、無晉升")
    ok(guard5 == ("empty_day", None), "空手日回報 empty_day 護欄")

    # 防縮水：即使上游異常導致合併結果變少，也不覆寫
    shrunk, _, guard6 = m(hist, ["2330"], TODAY)
    ok(guard6 is None, "正常合併不會觸發縮水護欄")
    big_hist = {str(i): {"count": 1, "last_date": ""} for i in range(10)}
    new7, _, guard7 = m(big_hist, [], TODAY)
    ok(len(new7) == 10, "10 筆歷史在空手日維持 10 筆")

    # 空歷史起步
    new8, _, guard8 = m({}, ["1101", "2330"], TODAY)
    ok(len(new8) == 2 and guard8 is None, "空歷史起步可正常寫入 2 筆")


# =====================================================================
# ③ 姊夫池貴金屬 ETF 固定名單（V9.3：V9.2 動態篩選已移除）
# =====================================================================
def test_jiefu_etf_pool():
    section("③ 姊夫池貴金屬 ETF 固定名單（V9.3）")
    ok(radar.JIEFU_ETF_POOL == ["00635U", "00708L", "00674R", "00738U"],
       f"名單為圖表指定的 4 檔（實得 {radar.JIEFU_ETF_POOL}）")
    ok(radar.POOL_SETTINGS["🔥 姊夫爆發小魚池"] == radar.JIEFU_ETF_POOL,
       "POOL_SETTINGS 與 JIEFU_ETF_POOL 一致（不會出現空池日）")
    ok(list(radar.JIEFU_ETF_PARAMS.keys()) == radar.JIEFU_ETF_POOL,
       "參數表覆蓋全部成員，無漏設")

    for sid, cfg in radar.JIEFU_ETF_PARAMS.items():
        need = {"label", "underlying", "kind", "direction", "leverage",
                "stop_pct", "target_pct", "note"}
        ok(need <= set(cfg), f"{sid} 參數欄位齊全")
        ok(0 < cfg["stop_pct"] <= 0.15, f"{sid} 停損幅度在合理區間（{cfg['stop_pct']:.0%}）")

    ok(radar.JIEFU_ETF_PARAMS["00674R"]["direction"] == "空", "00674R 標記為反向（空方向）")
    ok(radar.JIEFU_ETF_PARAMS["00708L"]["leverage"] == 2.0, "00708L 標記為 2 倍槓桿")
    ok(radar.JIEFU_ETF_PARAMS["00708L"]["stop_pct"] > radar.JIEFU_ETF_PARAMS["00635U"]["stop_pct"],
       "槓桿商品停損幅度大於原型（避免被 2 倍波動頻繁掃出）")

    # V9.2 的動態篩選與融資閘門必須確實移除，避免死碼殘留
    for gone in ("_select_jiefu_pool", "_is_excluded_industry",
                 "_check_margin_not_surging", "JIEFU_EXCLUDED_INDUSTRIES"):
        ok(not hasattr(radar, gone), f"V9.2 殘留已移除：{gone}")


# =====================================================================
# ④ 姊夫池分級停損停利與建議部位
# =====================================================================
def test_jiefu_risk_params():
    section("④ 姊夫池分級停損停利（依商品槓桿倍數）")
    d = radar._apply_jiefu_risk_params(
        {"stock_id": "00635U", "close": 100.0, "stop_loss": 90.0, "stop_loss_mode": "ATR"})
    ok(d["stop_loss"] == 93.0, "原型 ETF 停損 = 收盤 ×0.93（−7%），覆蓋 ATR 動態停損")
    ok(d["target_price"] == 108.0 and d["first_target"] == 108.0, "原型 ETF 停利 = 收盤 ×1.08（+8%）")
    ok(d["stop_loss_mode"] == "JIEFU_ETF_7PCT", "停損模式標記為姊夫池 ETF 分級值")
    ok(d["suggested_position"] == 29000, "建議部位 = 2000/0.07 取千位 ≈ 29,000 元")
    ok(d["etf_kind"] == "原型" and d["etf_note"], "帶出商品類型與風險說明欄位")

    lev = radar._apply_jiefu_risk_params({"stock_id": "00708L", "close": 100.0})
    ok(lev["stop_loss"] == 90.0 and lev["target_price"] == 112.0, "槓桿 ETF 為 −10%／+12%")
    ok(lev["stop_loss_mode"] == "JIEFU_ETF_10PCT", "槓桿 ETF 停損模式標記正確")
    ok(lev["suggested_position"] == 20000, "停損放寬 → 建議部位自動縮小為 20,000 元")

    rev = radar._apply_jiefu_risk_params({"stock_id": "00674R", "close": 100.0})
    ok(rev["stop_loss"] == 93.0 and rev["etf_direction"] == "空", "反向 ETF 為 −7%／方向標記為空")

    # 防禦性容錯
    unknown = radar._apply_jiefu_risk_params({"stock_id": "9999", "close": 100.0})
    ok(unknown["stop_loss"] == 93.0 and "etf_note" not in unknown,
       "未知代號 → 採 7%／8% 預設，不寫入 ETF 說明欄位")
    bad = radar._apply_jiefu_risk_params({"stock_id": "00635U", "close": 0, "stop_loss": 90.0})
    ok(bad["stop_loss"] == 90.0 and "suggested_position" not in bad, "收盤價為 0 → 原樣返回，不覆寫")
    bad2 = radar._apply_jiefu_risk_params({"stock_id": "00635U", "stop_loss": 90.0})
    ok("suggested_position" not in bad2, "缺 close 欄位 → 原樣返回，不炸")


# =====================================================================
# ⑤ 姊夫池 ETF 技術訊號（取代失真的法人條件）
# =====================================================================
def test_jiefu_etf_signal():
    section("⑤ 姊夫池 ETF 技術訊號（close ≥ MA5 且 量比 ≥ 1.0）")
    buy = radar._apply_jiefu_etf_signal(
        {"stock_id": "00635U", "close": 47.0, "ma5": 46.0, "vol_ratio": 1.3, "inst_buy": -9999})
    ok(buy["action"] == "買入加碼", "站上 MA5 且量比達標 → 買入加碼（法人淨賣不影響）")
    ok("不採法人條件" in buy["action_basis"], "訊號依據欄位載明不採法人條件")
    ok("自營商避險" in buy["chip_note"], "附上 ETF 籌碼解讀說明")

    below = radar._apply_jiefu_etf_signal(
        {"stock_id": "00635U", "close": 45.0, "ma5": 46.0, "vol_ratio": 2.0, "inst_buy": 99999})
    ok(below["action"] == "靜候觀察", "跌破 MA5 → 靜候觀察（法人大買也不成立）")

    thin = radar._apply_jiefu_etf_signal(
        {"stock_id": "00635U", "close": 47.0, "ma5": 46.0, "vol_ratio": 0.9})
    ok(thin["action"] == "靜候觀察", "量比 0.9 < 1.0 → 靜候觀察")

    edge = radar._apply_jiefu_etf_signal(
        {"stock_id": "00635U", "close": 46.0, "ma5": 46.0, "vol_ratio": 1.0})
    ok(edge["action"] == "買入加碼", "收盤等於 MA5 且量比恰為 1.0 → 成立（邊界）")

    rev = radar._apply_jiefu_etf_signal(
        {"stock_id": "00674R", "close": 27.0, "ma5": 26.5, "vol_ratio": 1.5})
    ok("金價下跌" in rev["signal_direction_note"], "反向 ETF 訊號標註為偏空方向，避免誤讀成看多金價")

    fwd = radar._apply_jiefu_etf_signal(
        {"stock_id": "00738U", "close": 55.0, "ma5": 54.0, "vol_ratio": 1.5})
    ok("白銀期貨" in fwd["signal_direction_note"], "原型 ETF 標註對應標的方向")

    # 防禦性容錯
    miss = radar._apply_jiefu_etf_signal({"stock_id": "00635U", "close": 47.0})
    ok("action" not in miss, "缺 MA5 → 不覆寫 action，不炸")
    novr = radar._apply_jiefu_etf_signal({"stock_id": "00635U", "close": 47.0, "ma5": 46.0})
    ok(novr["action"] == "靜候觀察", "量比欄位缺漏 → 視為 0，保守判為靜候觀察")


# =====================================================================
# ⑥ 大盤環境三段式與 rsi_ceiling（以假資料替換 yfinance，全程離線）
# =====================================================================
class _FakeTicker:
    def __init__(self, values):
        self._values = values

    def history(self, *a, **k):
        return pd.DataFrame({"Close": [float(v) for v in self._values]})


class _FakeYF:
    def __init__(self, values):
        self._values = values

    def Ticker(self, *a, **k):
        return _FakeTicker(self._values)


# 期望值來自規格表，與 radar 實作各自獨立：
#   收盤 ≥ MA60 且 MA60 上彎 → 多頭（門檻 2000／1.2、折扣 1.00、RSI 上限 80）
#   收盤 ≥ MA60 且 MA60 下彎 → 中性（2500／1.35、0.92、75）
#   收盤 <  MA60             → 空頭（3000／1.5、0.85、70）
_REGIME_TABLE = {
    "多頭": (2000, 1.2, 1.00, 80),
    "中性": (2500, 1.35, 0.92, 75),
    "空頭": (3000, 1.5, 0.85, 70),
}

_FIXTURES = [
    ("多頭", [100 + i for i in range(70)]),                                  # 一路走高
    ("空頭", [300 - i * 2 for i in range(70)]),                              # 一路走低
    ("中性", [300 - i * 3 for i in range(60)] + [135 + i * 12 for i in range(10)]),  # 長空後急彈，MA60 仍下彎
]


def test_market_regime():
    section("⑥ 大盤環境三段式與 rsi_ceiling（離線假資料）")
    original = radar.yf
    seen = set()
    try:
        for expected, values in _FIXTURES:
            radar.yf = _FakeYF(values)
            r = radar._calc_market_regime()
            seen.add(r["regime"])
            ok(r["regime"] == expected, f"{expected} 情境判定正確（收盤 {r['twii_close']} vs MA60 {r['twii_ma60']}）")
            vt, vr, sf, rc = _REGIME_TABLE[expected]
            ok((r["vol_threshold"], r["volratio_threshold"], r["score_factor"], r["rsi_ceiling"]) == (vt, vr, sf, rc),
               f"{expected} 的量能 {vt}／量比 {vr}／折扣 {sf}／RSI 上限 {rc} 全部對齊")

        # 資料不足或抓取失敗一律回預設多頭門檻（不誤殺）
        radar.yf = _FakeYF([100] * 10)
        ok(radar._calc_market_regime()["rsi_ceiling"] == 80, "資料不足 65 筆 → 回預設多頭門檻（不誤殺）")

        class _Boom:
            def Ticker(self, *a, **k):
                raise RuntimeError("yfinance 異常")
        radar.yf = _Boom()
        d = radar._calc_market_regime()
        ok(d["regime"] == "多頭" and d["rsi_ceiling"] == 80, "yfinance 拋例外 → 回預設多頭門檻（不誤殺）")
    finally:
        radar.yf = original

    ok(seen == {"多頭", "中性", "空頭"}, "三種環境分支皆已實際走過（測資未失效）")


TESTS = [
    test_ocean_gates,
    test_merge_ocean_history,
    test_jiefu_etf_pool,
    test_jiefu_risk_params,
    test_jiefu_etf_signal,
    test_market_regime,
]


def main():
    print("=" * 64)
    print(f"🧪 V9.x 閘門離線回歸測試（radar {radar.RADAR_VERSION}）")
    print("=" * 64)
    for t in TESTS:
        t()
    print("\n" + "=" * 64)
    print(f"✅ 全數通過：{_checks} 項斷言")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
