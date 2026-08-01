"""
tests/run_all.py — 離線測試批次入口（稽核 D3）

執行：python tests/run_all.py
性質：全程離線 —— 不呼叫 FinMind、不連 yfinance、不推送。可安全於任何時間執行。

納入批次：
  test_gates.py    V9.x 選股閘門回歸測試（純假資料）

不納入批次（需連網，請手動執行）：
  manual_atr_stop.py        ATR×2 動態停損實測（yfinance 抓真實股價）
  manual_market_regime.py   大盤環境實測（yfinance 抓 ^TWII）
  verify_v89.py             戰報輸出唯讀驗收（須先有當日戰報，非邏輯回歸測試）
"""
import sys
import os
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_gates

SUITES = [
    ("V9.x 閘門回歸", test_gates.main),
]


def main():
    failed = []
    for name, run in SUITES:
        try:
            run()
        except Exception:
            failed.append(name)
            print(f"\n❌ {name} 失敗：")
            traceback.print_exc()

    print()
    if failed:
        print(f"❌ 共 {len(failed)} 組測試未通過：{'、'.join(failed)}")
        return 1
    print(f"🎉 全部 {len(SUITES)} 組離線測試通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
