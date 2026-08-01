# ==========================================
# verify_v89.py — V8.9 上線後唯讀驗收腳本（任務1~4）
# ==========================================
# 用途：明日 Moly 跑完後，一鍵核對 plum/log/回測/題材 四份輸出。
# 性質：唯讀，不修改任何檔案、不呼叫 API、不推送。
# 執行：python verify_v89.py
# ==========================================
import sys, io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import json
import os
from datetime import datetime, timezone, timedelta

# 2026-08-01（稽核 D3）移入 tests/ 後，戰報 JSON 仍在專案根目錄，
# 故切換工作目錄，讓下方 load_json 的相對路徑維持原樣運作。
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TW_TZ = timezone(timedelta(hours=8))
PASS, FAIL, WARN = "✅", "❌", "⚠️"
_results = []  # (status, message)


def chk(cond, ok_msg, fail_msg, warn=False):
    mark = PASS if cond else (WARN if warn else FAIL)
    _results.append((mark, ok_msg if cond else fail_msg))
    print(f"  {mark} {ok_msg if cond else fail_msg}")
    return cond


def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  {FAIL} 讀取 {path} 失敗：{e}")
        return None


def section(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")


# =====================================================================
# ① plum_blossom_data.json — 新欄位
# =====================================================================
def verify_plum():
    section("① plum_blossom_data.json 新欄位（任務2/3）")
    d = load_json("plum_blossom_data.json")
    if d is None:
        chk(False, "", "plum_blossom_data.json 不存在或無法讀取")
        return
    print(f"  ℹ️ last_updated = {d.get('last_updated', '—')}")

    # 任務3：market_regime
    mr = d.get("market_regime")
    if chk(isinstance(mr, dict) and mr.get("regime"),
           f"market_regime 存在：{mr.get('regime') if isinstance(mr, dict) else ''} "
           f"(加權 {mr.get('twii_close') if isinstance(mr, dict) else ''} vs MA60 "
           f"{mr.get('twii_ma60') if isinstance(mr, dict) else ''})",
           "market_regime 區塊缺失（任務3 未生效，radar 可能仍為舊版）"):
        for k in ("vol_threshold", "volratio_threshold", "score_factor", "emoji"):
            chk(k in mr, f"market_regime.{k} = {mr.get(k)}", f"market_regime 缺欄位 {k}")

    # 收集所有個股卡
    pools = d.get("pools", {})
    all_cards = [s for v in pools.values() for s in v if isinstance(s, dict)]
    print(f"  ℹ️ 個股卡總數 = {len(all_cards)}")
    if not all_cards:
        chk(False, "", "無任何個股卡，無法檢查停損欄位")
        return

    # 任務2：ATR 停損欄位（取有 close 數值的卡）
    valued = [s for s in all_cards if isinstance(s.get("close"), (int, float)) and s.get("close")]
    sample = valued[0] if valued else all_cards[0]
    for f in ("atr14", "atr_pct", "stop_loss_mode", "stop_loss_fixed"):
        chk(f in sample, f"個股卡含欄位 {f}（樣本 {sample.get('stock_id')}）",
            f"個股卡缺欄位 {f}（任務2 未生效）")

    # stop_loss_mode 分布
    modes = {}
    for s in all_cards:
        m = s.get("stop_loss_mode", "缺")
        modes[m] = modes.get(m, 0) + 1
    print(f"  ℹ️ stop_loss_mode 分布：{modes}")
    chk(any(m == "ATR" for m in modes),
        "至少有個股使用 ATR 模式停損", "無 ATR 模式（檢查 High/Low 來源）", warn=True)

    # stop_loss 是否為動態（與 close×0.9 不同）
    dyn_count = 0
    for s in valued:
        c = s.get("close")
        sl = s.get("stop_loss")
        if isinstance(sl, (int, float)) and abs(sl - round(c * 0.9, 2)) > 0.01:
            dyn_count += 1
    chk(dyn_count > 0,
        f"{dyn_count}/{len(valued)} 檔 stop_loss 已動態（≠ close×0.9）",
        "所有 stop_loss 仍等於 close×0.9（動態停損未生效）", warn=True)

    # 護欄檢查：動態停損應落在 [0.85×close, 0.94×close]（容忍 1 分量化誤差）
    out_of_band = []
    for s in valued:
        c, sl, mode = s.get("close"), s.get("stop_loss"), s.get("stop_loss_mode")
        if mode in ("ATR", "VOL_FALLBACK") and isinstance(sl, (int, float)) and c:
            lower = round(c * 0.85, 2) - 0.01  # 容忍分量化
            upper = round(c * 0.94, 2) + 0.01
            if sl < lower or sl > upper:
                out_of_band.append((s.get("stock_id"), round((sl / c - 1) * 100, 2)))
    chk(not out_of_band,
        "所有動態停損落在護欄 -6%~-15% 內（含分量化容忍）",
        f"有 {len(out_of_band)} 檔超出護欄：{out_of_band[:5]}")

    # Bug-01：price_date
    missing_pd = [s.get("stock_id") for s in all_cards
                  if not s.get("price_date") or s.get("price_date") == "0000-00-00"]
    chk(len(missing_pd) == 0,
        "全數個股卡 price_date 正常（Bug-01 無回歸）",
        f"{len(missing_pd)} 檔 price_date 異常：{missing_pd[:5]}", warn=True)


# =====================================================================
# ② log_report.json — 排程健康
# =====================================================================
def verify_log():
    section("② log_report.json 排程健康")
    d = load_json("log_report.json")
    if d is None:
        chk(False, "", "log_report.json 不存在")
        return
    print(f"  ℹ️ last_update = {d.get('last_update', '—')} | status = {d.get('status', '—')}")
    chk(d.get("status") == "Success", "status = Success", f"status = {d.get('status')}（非 Success）", warn=True)
    chk("push_status" not in d,
        "log_report.json 不含 push_status（E5 已生效，該檔提交後保持乾淨）",
        "log_report.json 仍含 push_status —— E5 修正被回退，工作區將恆為 dirty")

    # 推送狀態自 2026-08-01（稽核 E5）起改存本機 push_status.json（不進版控）
    p = load_json("push_status.json")
    if p is None:
        chk(False, "", "push_status.json 不存在（radar.py 尚未於本機跑過推送段）", warn=True)
    elif p.get("last_update") != d.get("last_update"):
        chk(False, "", f"push_status.json 為上一輪殘留（{p.get('last_update')}），非本輪結果")
    else:
        chk(p.get("push_status") == "OK",
            "push_status = OK", f"push_status = {p.get('push_status')}（推送異常）")
    print(f"  ℹ️ API 消耗 = {d.get('api_usage_count', '—')}、快取命中 = {d.get('cache_hits', '—')}、"
          f"處理 = {d.get('stocks_processed', '—')} 檔")


# =====================================================================
# ③ backtest_report.json — 週六回測（任務1）
# =====================================================================
def verify_backtest():
    section("③ backtest_report.json 回測報告（任務1，週六排程）")
    d = load_json("backtest_report.json")
    if d is None:
        chk(False, "", "backtest_report.json 不存在（週六排程尚未跑或失敗）", warn=True)
        return
    print(f"  ℹ️ generated_at = {d.get('generated_at', '—')} | benchmark = {d.get('benchmark', '—')}")
    pools = d.get("pools", {})
    expect = ["🌟 彼神黃金魚池", "🔥 姊夫爆發小魚池", "🍁 楓大永動魚池", "🔭 測試員觀察水域", "🃏 被動卡娃魚池"]
    chk(all(p in pools for p in expect),
        f"5 個目標魚池齊全（{len(pools)} 池）",
        f"缺魚池：{[p for p in expect if p not in pools]}")
    chk("🌊 汪洋大魚" not in pools and "🐅 三日成猛虎水池" not in pools,
        "已正確排除汪洋大魚與猛虎池", "回測含不應出現的池（汪洋/猛虎）")


# =====================================================================
# ④ grace_theme_data.json — 週日題材（任務4）
# =====================================================================
def verify_grace():
    section("④ grace_theme_data.json 題材分析（任務4，週日排程）")
    d = load_json("grace_theme_data.json")
    if d is None:
        chk(False, "", "grace_theme_data.json 不存在（週日排程尚未跑或失敗）", warn=True)
        return
    print(f"  ℹ️ last_updated = {d.get('last_updated', '—')} | 基準日 = {d.get('source_price_date', '—')}")
    stat = d.get("stat", {})
    print(f"  ℹ️ 持續性統計：高 {stat.get('high')} / 中 {stat.get('mid')} / 低 {stat.get('low')} / 合計 {stat.get('total')}")
    tiers = d.get("tiers", {})
    total_cards = sum(len(v) for v in tiers.values())
    chk(total_cards > 0, f"題材卡 {total_cards} 檔（Tier 分層 {list(tiers.keys())}）", "無題材卡")
    # 抽查第一張卡 Grace 格式四要素
    first = next((c for v in tiers.values() for c in v), None)
    if first:
        need = ("theme_type", "catalyst", "sustainability_level", "risk")
        chk(all(k in first for k in need),
            f"Grace 格式四要素齊全（樣本 {first.get('stock_id')}）",
            f"缺要素：{[k for k in need if k not in first]}")


def main():
    print("=" * 60)
    print(f"🔍 V8.9 上線驗收（唯讀）  執行時間：{datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    verify_plum()
    verify_log()
    verify_backtest()
    verify_grace()

    section("📊 驗收總結")
    n_pass = sum(1 for m, _ in _results if m == PASS)
    n_fail = sum(1 for m, _ in _results if m == FAIL)
    n_warn = sum(1 for m, _ in _results if m == WARN)
    print(f"  {PASS} 通過 {n_pass}　{WARN} 警告 {n_warn}　{FAIL} 失敗 {n_fail}")
    if n_fail:
        print(f"\n  {FAIL} 失敗項目：")
        for m, msg in _results:
            if m == FAIL:
                print(f"     - {msg}")
    if n_warn:
        print(f"\n  {WARN} 警告項目（可能為排程時序，如週六/日尚未跑）：")
        for m, msg in _results:
            if m == WARN:
                print(f"     - {msg}")
    print("\n" + ("🎉 全數通過，V8.9 上線正常！" if n_fail == 0 else "⚠️ 有失敗項目，請依上方清單診斷。"))
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
