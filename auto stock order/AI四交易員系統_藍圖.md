# 彼夫有責戰情室 — AI 四交易員量化系統藍圖（永豐 Shioaji 模擬帳戶）

> 版本：Blueprint V0.2（依影片分級架構校準）
> 建立：2026-06-14
> 負責人：JW
> 定位：戰情室選股引擎（radar.py）的「**下單執行層**」，獨立子專案 `auto stock order/`
> 安全前提：**全程模擬帳戶（simulation=True），不接觸真實資金，未經 JW 明確同意不得切換實盤**

---

## 0. 影片分級 → 系統映射（校準後）

影片以「Level 漸進」教學，本藍圖將其映射為戰情室的 **4 名 AI 交易員 + 基礎建設層 + 推播層**：

| 影片 Level | 內容 | 本系統角色 |
|---|---|---|
| **Level 1** | 連線券商、自動下單（Shioaji 模擬） | **基礎建設層**（執行引擎，非交易員） |
| **Level 2** | 抄底機器人：跌 1% 買 1 股／跌 2% 買 2 股 + Trailing Stop | **交易員① 抄底員 DipBot** |
| **Level 3** | Insider 內部人交易追蹤（內部大股東買賣） | **交易員② 內部人員 Insider** |
| **Level 3+** | 主力籌碼跟單（主力/法人/籌碼大戶） | **交易員③ 主力跟單員 SmartMoney** |
| **Level 4** | 大股東質設增加 ＋ 融資低檔突然暴增 | **交易員④ 質融偵察員 Leverage** |
| **Bonus** | 全自動排程 + Telegram 手機推播 | **推播/排程層** |

> 4 名交易員各自獨立評分投票 → 風控組合經理彙整下單 → 基礎建設層執行 → 推播層通知。

---

## 1. 系統總目標

將戰情室現有選股訊號（`plum_blossom_data.json`）與**四種獨立 alpha 來源**（抄底、內部人、主力籌碼、質融異常）交由 4 名 AI 交易員評分，經風控組合經理彙整成部位指令，透過**永豐 Shioaji 模擬帳戶**自動掛單，並以 Telegram 推播機會與成交回報。

---

## 2. 系統總架構圖

```
┌──────────────────────────────────────────────────────────────┐
│  上游資料源                                                     │
│  ① radar.py → plum_blossom_data.json（候選股/籌碼/強勢評分）    │
│  ② FinMind（法人、融資融券、股權分散）                         │
│  ③ MOPS 公開資訊觀測站（內部人申報轉讓、董監質設）【需驗證】    │
│  ④ Shioaji 即時報價（盤中跌幅監控）                            │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  決策層：4 名 AI 交易員（各自 signal -100~+100 + confidence）   │
│  ① 抄底員 DipBot   ② 內部人員 Insider                          │
│  ③ 主力跟單員 SmartMoney   ④ 質融偵察員 Leverage               │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  風控組合經理 RiskMgr（加權彙整 + 部位 sizing + 風控閘門）      │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  基礎建設層：Shioaji 下單引擎（simulation=True）               │
│  • 整股 + 盤中零股 + Trailing Stop 軟體實作 + 對帳             │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  推播/回饋層：Telegram Bot + trades.json + portfolio.json      │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. ⚠️ 資料源可行性查核（證據優先，先做這件事）

台股的四種 alpha，**資料可得性差異極大**，須誠實分級。實作前以最小範例驗證每一項。

| 交易員 | 所需資料 | 來源 | 可行性 | 備註 |
|---|---|---|---|---|
| ① 抄底 | 即時/當日跌幅、成本均價 | Shioaji 報價 + 自建持倉 | 🟢 高 | 純價格邏輯，最易落地 |
| ③ 主力跟單 | 三大法人買賣超 | FinMind `TaiwanStockInstitutionalInvestorsBuySell` | 🟢 高 | 戰情室已在用 |
| ④ 融資暴增 | 融資融券餘額 | FinMind `TaiwanStockMarginPurchaseShortSale` | 🟢 高 | 「低檔 + 融資暴增」可算 |
| ③ 籌碼大戶 | 集保股權分散（千張大戶） | FinMind `TaiwanStockHoldingSharesPer`【需驗證欄位】 | 🟡 中 | 週頻資料、延遲 |
| ② 內部人 | 內部人持股/申報轉讓 | MOPS 公開資訊觀測站 | 🟠 低-中 | **FinMind 可能無，須爬 MOPS** |
| ④ 大股東質設 | 董監股權設質解質 | MOPS「股權設質解質」 | 🟠 低-中 | **須爬 MOPS，資料延遲** |

> 【資料不足，待驗證】②內部人 與 ④質設 兩項，FinMind 是否有現成 dataset 尚未確認；若無，需以 MOPS 爬蟲取得（更新頻率低、有申報延遲）。**建議落地順序：① → ③ → ④融資 → ④質設/②內部人**（由易到難）。

---

## 4. 四名 AI 交易員設計

統一介面：輸入候選股，輸出 `signal`（-100 賣~+100 買）、`confidence`（0~1）、繁中理由。

### 交易員① 抄底員 DipBot（Level 2）★ 最先落地

**邏輯**：對「鎖定標的」分批向下承接，搭配 Trailing Stop 出場。

| 規則 | 說明 |
|---|---|
| 觸發 | 自參考價（如當日開盤/前收）跌幅達門檻分批買 |
| 加碼階梯 | 跌 1% → 買 1 單位；跌 2% → 買 2 單位；可線性/金字塔加碼 |
| 單位定義 | **台股「買 1 股」＝盤中零股交易**（Shioaji `order_lot=IntradayOdd`） |
| Trailing Stop | 軟體實作：記錄持有期最高價，回檔達 X%（如 5%）觸發賣出 |
| 護欄 | 單檔承接總額上限、跌停/異常不接、總抄底預算上限 |

```python
class DipBot(BaseTrader):
    name = "抄底員DipBot"
    def evaluate(self, stock, market):
        drop = (stock["ref_price"] - stock["last_price"]) / stock["ref_price"] * 100
        if drop < 1:        # 未達抄底門檻
            return self._flat(stock)
        units = int(drop)   # 跌1%→1、跌2%→2…（可改金字塔）
        units = min(units, self.max_units)
        return {"trader": self.name, "ticker": stock["ticker"],
                "signal": min(100, 20*units), "confidence": 0.6,
                "reason": f"跌{drop:.1f}%→分批承接{units}單位（零股）"}
    # Trailing Stop 由 RiskMgr 持倉監控統一執行
```

### 交易員② 內部人員 Insider（Level 3）

**邏輯**：追蹤內部大股東（董監、經理人、10% 以上大股東）申報轉讓/持股異動，**內部人增持＝正訊號、申報大量轉讓（賣）＝負訊號**。資料源見 §3（須驗證 MOPS）。

### 交易員③ 主力跟單員 SmartMoney（Level 3+）

**邏輯**：跟單三大法人 + 籌碼大戶。沿用戰情室既有欄位 `inst_buy`/`foreign_buy`/`trust_buy`/`chip_signal`/`inst_grade`，外加集保千張大戶持股比變化。外資+投信雙買且大戶增持＝強訊號。

### 交易員④ 質融偵察員 Leverage（Level 4）

**邏輯（雙因子）**：
- **大股東質設增加**：董監質押比上升＝警訊（潛在賣壓/財務壓力）→ 偏負，或作為**排除過濾**。
- **融資低檔暴增**：股價處低檔但融資餘額短期暴增＝散戶搶進、籌碼凌亂 → 偏負（反指標）；反之**融資減少＋法人進場**＝籌碼換手健康 → 偏正。

> 此員多為**風險過濾/反指標**性質，權重設計上偏向「否決票」而非「買票」。

---

## 5. 風控組合經理（RiskMgr）

唯一能下單的角色，集中所有風險閘門。

**彙整**：`綜合分數 = Σ(signal × confidence × weight) / Σ(weight)`

| 綜合分數 | 動作 |
|---|---|
| ≥ +60 | 強力買進（單檔上限） |
| +30~+60 | 買進（半倉） |
| -30~+30 | 持有/觀望 |
| -60~-30 | 減碼 |
| ≤ -60 | 出清 |

**硬閘門**：單檔 ≤15%、總曝險 ≤80%、持股 ≤8 檔、空頭環境 sizing×0.5、ATR×2 停損（沿用 radar 欄位）、**Trailing Stop 統一監控**、單日下單次數上限、流動性 <1,000 張不進、跌停不接。

---

## 6. 基礎建設層：Shioaji（Level 1）

> ⚠️ Shioaji SDK 用法示意，**確切簽章以永豐官方當前文件為準**【需驗證】。

```bash
pip install shioaji
```

```python
import shioaji as sj, os
api = sj.Shioaji(simulation=True)                      # ★ 模擬帳戶
api.login(api_key=os.environ["SHIOAJI_API_KEY"],
          secret_key=os.environ["SHIOAJI_SECRET"])     # 金鑰走環境變數，不進版控

contract = api.Contracts.Stocks.TSE["2330"]
order = api.Order(
    price=600, quantity=1,
    action=sj.constant.Action.Buy,
    price_type=sj.constant.StockPriceType.LMT,
    order_type=sj.constant.OrderType.ROD,
    order_lot=sj.constant.StockOrderLot.IntradayOdd,   # ★ 盤中零股（買 1 股關鍵）
    account=api.stock_account)
trade = api.place_order(contract, order)
```

**Trailing Stop**：Shioaji 股票無原生移動停損，**須軟體實作**——持倉監控記錄最高價，回檔達閾值即送賣單。

---

## 7. 推播層：Telegram Bot（Bonus）

```python
import requests, os
def push(msg):
    requests.post(
        f"https://api.telegram.org/bot{os.environ['TG_BOT_TOKEN']}/sendMessage",
        json={"chat_id": os.environ["TG_CHAT_ID"], "text": msg})
```

觸發時機：掃到抄底機會、內部人/主力異動、成交回報、停損出場、每日淨值結算。

---

## 8. 檔案結構（建議）

```
auto stock order/
├── AI四交易員系統_藍圖.md
├── config.yaml                  # simulation 旗標、權重、風控門檻、資金
├── traders/
│   ├── base_trader.py
│   ├── dip_bot.py               # ① 抄底（Level 2）
│   ├── insider_trader.py        # ② 內部人（Level 3）
│   ├── smartmoney_trader.py     # ③ 主力跟單（Level 3+）
│   └── leverage_trader.py       # ④ 質融（Level 4）
├── risk_manager.py
├── broker_shioaji.py            # Shioaji 封裝 + Trailing Stop 監控
├── datasources/
│   ├── finmind_feed.py          # 法人、融資、股權分散
│   └── mops_feed.py             # 內部人、質設【需驗證】
├── notify_telegram.py
├── main.py
├── state/{portfolio,trades,decisions}.json
└── dashboard.html
```

---

## 9. 開發路線圖（由易到難，對齊資料可行性）

| 階段 | 內容 | 驗收 |
|---|---|---|
| **P0** | Shioaji 模擬登入 + 查 2330 合約 + 查庫存 + **盤中零股下單測試** | 模擬帳戶看到零股委託 |
| **P1** | 交易員① 抄底員 + Trailing Stop（純價格，無需外部資料） | 模擬跌幅觸發分批承接 + 回檔出場 |
| **P2** | 交易員③ 主力跟單（FinMind 法人，戰情室已有） | 法人雙買標的產生買訊 |
| **P3** | 交易員④ 融資暴增（FinMind 融資融券） | 低檔融資暴增標的產生風險訊號 |
| **P4** | 交易員②內部人 + ④質設（MOPS 爬蟲，先驗資料源） | 能取得並解析 MOPS 資料 |
| **P5** | RiskMgr 彙整 + Telegram 推播 + 排程接 Moly | 無人值守模擬連跑 N 日 + 手機收推播 |
| **P6** | 實盤閘門：風險審查 + JW 明確同意 + 小額試單 | **需 JW 簽核，預設不執行** |

---

## 10. 風險與紀律

| 風險 | 對策 |
|---|---|
| 模擬→實盤誤切 | `simulation` 集中 config，預設 True，切換需二次確認 |
| API 金鑰/TG Token 外洩 | 一律環境變數 + `.gitignore`，不進版控 |
| 抄底接刀（一路下跌） | 單檔承接上限 + 總抄底預算 + 跌停不接 + Trailing Stop |
| 內部人/質設資料延遲失真 | 標註資料時間戳，延遲資料降權，僅作輔助非主訊號 |
| 過度交易 | 單日下單上限 + 流動性過濾 |
| 系統當機 | 全域 kill switch + 大盤空頭降權 |

---

## 11. 與既有戰情室整合

| 既有資產 | 整合 |
|---|---|
| `plum_blossom_data.json` | 主力跟單員③ 的候選與籌碼來源（不改動 radar.py） |
| FinMind 快取機制 | datasources/finmind_feed.py 沿用降載策略 |
| `market_regime` 大盤三段式 | RiskMgr 降權 |
| ATR×2 停損欄位 | RiskMgr 停損閘門 |
| Moly 本地排程 | P5 掛接 |

---

## 12. 下一步（待 JW 裁示）

1. **永豐 API Key 申請狀態？**（決定能否進 P0）
2. 是否先做 **P0 + P1**（Shioaji 模擬連線 + 抄底員）——這是影片 Level 1~2，純價格邏輯、不依賴難取得的外部資料，落地最快、最能先看到成果。
3. 內部人②/質設④資料源：先花半天**驗證 FinMind/MOPS 是否拿得到**，再決定是否納入第一版。
4. Telegram Bot Token 是否已備妥？

---

*本藍圖依影片分級架構校準。全程模擬，實盤需 JW 明確同意。資料可行性以實測為準。*
