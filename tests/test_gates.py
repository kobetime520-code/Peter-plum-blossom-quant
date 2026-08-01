"""
tests/test_gates.py — V9.x 選股閘門離線回歸測試（稽核 D3）

性質：純離線。不呼叫 FinMind、不連 yfinance、不讀寫戰報檔、不推送。
執行：python tests/run_all.py     （或 python tests/test_gates.py）

涵蓋範圍（皆為 V9.0～V9.2 新增、原本毫無自動化保護的邏輯）：
  ① A1 籌碼方向閘門 ＋ A2 追高防護     _passes_ocean_gates
  ② 記憶海真·僅追加 ＋ 防縮水護欄      merge_ocean_history
  ③ 姊夫池動態篩選                     _select_jiefu_pool / _is_excluded_industry
  ④ 姊夫池專屬停損停利                 _apply_jiefu_risk_params
  ⑤ 融資遽增風控閘門的容錯放行         _check_margin_not_surging
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
# ③ 姊夫池動態篩選
# =====================================================================
def _cand(sid, grade="S", trend="STRONG", breakout=2, industry="半導體業", score=90):
    return {
        "stock_id": sid, "inst_grade": grade, "trend_quality": trend,
        "ma5_breakout_day": breakout, "industry": industry, "strength_score": score,
    }


def test_jiefu_pool():
    section("③ 姊夫池動態篩選（inst_grade／trend／突破日／產業／排序）")
    ok(radar._is_excluded_industry("金融保險業") is True, "金融保險業 → 排除")
    ok(radar._is_excluded_industry("水泥工業") is True, "水泥工業（傳產）→ 排除")
    ok(radar._is_excluded_industry("半導體業") is False, "半導體業 → 不排除")
    ok(radar._is_excluded_industry("") is False, "產業別空字串 → 不排除（不誤殺）")

    pool = [
        _cand("A1", grade="S", score=95),
        _cand("A2", grade="A", score=80),
        _cand("B1", grade="B", score=99),                    # 籌碼等級不足
        _cand("C1", trend="WATCH", score=99),                # 趨勢品質不足
        _cand("D1", breakout=0, score=99),                   # 尚未站上 MA5
        _cand("D2", breakout=4, score=99),                   # 站上太久，非「剛突破」
        _cand("E1", industry="金融保險業", score=99),         # 產業排除
    ]
    got = [s["stock_id"] for s in radar._select_jiefu_pool(pool, top_n=8)]
    ok(got == ["A1", "A2"], f"四道條件全部生效，僅 A1／A2 入選（實得 {got}）")

    # 邊界：突破日 1 與 3 應通過
    edge = [_cand("F1", breakout=1), _cand("F2", breakout=3)]
    ok(len(radar._select_jiefu_pool(edge)) == 2, "突破日 1 與 3 皆通過（邊界）")

    # 依 strength_score 由高到低取前 N
    many = [_cand(f"S{i}", score=i) for i in range(12)]
    top = [s["stock_id"] for s in radar._select_jiefu_pool(many, top_n=8)]
    ok(top == [f"S{i}" for i in range(11, 3, -1)], "依 strength_score 降序取前 8 檔")
    ok(len(radar._select_jiefu_pool(many, top_n=8)) == 8, "上限 8 檔生效")
    ok(radar._select_jiefu_pool([]) == [], "空 market_pool 回傳空清單，不炸")


# =====================================================================
# ④ 姊夫池專屬停損停利
# =====================================================================
def test_jiefu_risk_params():
    section("④ 姊夫池專屬停損停利（−7%／+8%／建議部位）")
    d = radar._apply_jiefu_risk_params({"close": 100.0, "stop_loss": 90.0, "stop_loss_mode": "ATR"})
    ok(d["stop_loss"] == 93.0, "停損 = 收盤 ×0.93（−7%），覆蓋原本的 ATR 動態停損")
    ok(d["target_price"] == 108.0 and d["first_target"] == 108.0, "停利 = 收盤 ×1.08（+8%）")
    ok(d["stop_loss_mode"] == "JIEFU_FIXED_7PCT", "停損模式標記為姊夫池固定值")
    ok(d["suggested_position"] == 29000, "建議部位 = 2000/0.07 取千位 ≈ 29,000 元")

    # 防禦性容錯：不合法收盤價原樣返回，不得寫壞欄位
    bad = radar._apply_jiefu_risk_params({"close": 0, "stop_loss": 90.0})
    ok(bad["stop_loss"] == 90.0 and "suggested_position" not in bad, "收盤價為 0 → 原樣返回，不覆寫")
    bad2 = radar._apply_jiefu_risk_params({"stop_loss": 90.0})
    ok("suggested_position" not in bad2, "缺 close 欄位 → 原樣返回，不炸")


# =====================================================================
# ⑤ 融資遽增風控閘門（容錯放行，不誤殺）
# =====================================================================
def test_margin_gate():
    section("⑤ 融資遽增風控閘門（Eric，無資料時放行不誤殺）")
    original = radar.fetch_finmind
    try:
        def stub(df):
            return lambda *a, **k: df

        radar.fetch_finmind = stub(None)
        ok(radar._check_margin_not_surging("2330", "", "") == (True, 0.0), "API 回 None → 放行（不誤殺）")

        radar.fetch_finmind = stub(pd.DataFrame())
        ok(radar._check_margin_not_surging("2330", "", "") == (True, 0.0), "空 DataFrame → 放行")

        radar.fetch_finmind = stub(pd.DataFrame({"date": ["2026-07-31"], "other": [1]}))
        ok(radar._check_margin_not_surging("2330", "", "") == (True, 0.0), "缺融資餘額欄位 → 放行")

        def boom(*a, **k):
            raise RuntimeError("FinMind 異常")
        radar.fetch_finmind = boom
        ok(radar._check_margin_not_surging("2330", "", "") == (True, 0.0), "API 拋例外 → 放行（風控閘門不阻斷主流程）")

        # 融資平穩 → 通過；遽增 ≥30% → 攔截
        calm = pd.DataFrame({"date": ["2026-07-2%d" % i for i in range(1, 9)],
                             "MarginPurchaseTodayBalance": [1000, 1010, 1020, 1030, 1040, 1050, 1060, 1070]})
        radar.fetch_finmind = stub(calm)
        passed, pct = radar._check_margin_not_surging("2330", "", "")
        ok(passed is True and pct == 7.0, f"融資 10 日增 7% → 通過（實得 {pct}%）")

        surge = pd.DataFrame({"date": ["2026-07-2%d" % i for i in range(1, 9)],
                              "MarginPurchaseTodayBalance": [1000, 1100, 1200, 1250, 1300, 1350, 1400, 1500]})
        radar.fetch_finmind = stub(surge)
        passed, pct = radar._check_margin_not_surging("2330", "", "")
        ok(passed is False and pct == 50.0, f"融資 10 日增 50% ≥ 門檻 30% → 攔截（實得 {pct}%）")

        exact = pd.DataFrame({"date": ["a", "b"], "MarginPurchaseTodayBalance": [1000, 1300]})
        radar.fetch_finmind = stub(exact)
        passed, pct = radar._check_margin_not_surging("2330", "", "")
        ok(passed is False and pct == 30.0, "恰好 30% → 攔截（邊界為 <30 才通過）")
    finally:
        radar.fetch_finmind = original


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
    test_jiefu_pool,
    test_jiefu_risk_params,
    test_margin_gate,
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
