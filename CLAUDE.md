# 彼夫有責戰情室 — Claude 協作記憶檔

> 最後更新：2026-04-28
> 負責人：Jeff（kobetime520@gmail.com）

---

## 🎯 專案核心目標

建立一套台股**自動選股與監控系統**，以量化模型搭配三大法人籌碼，每日掃描股票池、輸出操作訊號，協助 Jeff 做出進出場決策。

---

## 📁 工作資料夾結構（最新）

| 路徑 | 說明 |
|---|---|
| `V7 daily json/` | 正式版每日選股快取（`plum_blossom_data.json`） |
| `V7 daily json test/` | 測試版每日選股快取 |
| `history/` | 正式版記憶海（`ocean_history.json`） |
| `history test/` | 測試版記憶海 |
| `auto radar yml/` | GitHub Actions 正式排程（`auto_radar.yml`，每日 20:39 台灣時間） |
| `auto radar yml test/` | GitHub Actions 測試版排程（僅 workflow_dispatch 手動觸發） |
| `radar/radar.py` | 核心雷達掃描程式（**靜水流深戰情室 V7.4**，正式版） |
| `radar test/radar.py` | 雷達沙盒（V7.4，與正式版同步） |
| `index/index.html` | 前端展示頁面（正式版） |
| `index test/index.html` | 前端測試版（新增深色/淺色海洋主題切換） |
| `測試 正式名稱轉換.docx` | 名稱轉換測試文件 |

---

## 🤖 GitHub Actions 自動排程

| 項目 | 說明 |
|---|---|
| 正式版排程 | 每週一～五，台灣時間 **20:39** 自動執行 |
| YAML 路徑 | `auto radar yml/auto_radar.yml` |
| 執行內容 | 安裝套件 → 執行 `radar.py` → 自動 commit & push 回倉庫 |
| 手動觸發 | GitHub Actions 頁面點擊 `workflow_dispatch` |
| 測試版 | `auto radar yml test/auto_radar.yml`（僅 workflow_dispatch，無 cron） |

---

## 🐠 魚池設定（Pool Settings）

| 魚池名稱 | 說明 | 目前股票數 |
|---|---|---|
| 🔥 姊夫爆發小魚池 | 短線爆發型股票 | 5 支 |
| 🍁 楓大永動魚池 | 穩定動能股 | 5 支 |
| 🌟 彼神黃金魚池 | 核心精選股 | 5 支 |
| 🔭 測試員觀察水域 | 觀察中候選股（含台積電、鴻海等大型股） | 9 支 |
| 🐅 三日成猛虎水池 | 短期強勢輪動（連續 3 日出現自動晉升） | 10 支 ✅ |
| 🌊 汪洋大魚 | 全市場掃描後符合條件的大量能強勢股 | 51 支 |

> 🐅 猛虎池條件：`history/ocean_history.json` 中出現次數 ≥ 3 次，自動加入

---

## ⚙️ 技術架構

### 資料來源
- **FinMind API**（主力精濾）：帳號 PeterJeff0226，綁定 kobetime520@gmail.com
- **Yahoo Finance yfinance**（全市場粗篩，批量下載每次 150 檔）

### V7.4 混合引擎流程
```
Yahoo Finance 全市場批量粗篩（chunk=150）
  ↓ 量能門檻：成交量 ≥ 1,500 張 + 收盤價 > MA30
FinMind 精確股價＋法人籌碼細部製卡
  ↓ 動作訊號判斷
輸出至 plum_blossom_data.json
```

### V7.4 核心功能
- **本地快取**：`finmind_cache.json` 避免重複呼叫 API
- **API 計數器**：`_api_calls_count` 精確計算（快取命中不計）
- **粗篩門檻**：成交量 ≥ **1,500 張**（縮圈戰術）
- **雙重火力補抓**：Yahoo 備援機制，確保資料完整

### 核心指標
- 收盤價（Close）、成交量（Volume，單位：張）
- MA5、MA30
- 三大法人 30 日買賣超：`inst_buy`（合計）、`foreign_buy`（外資）、`trust_buy`（投信）
- 目標價 = 收盤 × 1.5、停損價 = 收盤 × 0.9

### 動作訊號邏輯
```python
action = "買入加碼" if close_price >= ma5 and inst_buy_30d > 0 else "靜候觀察"
```

---

## 📊 最新戰情快照（2026-04-28 00:32）

| 項目 | 數值 |
|---|---|
| 最後更新時間 | 2026/04/28 00:32 |
| FinMind API 消耗 | 501 次（快取節省不計） |
| 🐅 猛虎池活躍股 | 10 支（6234、2486、2454、6274、3035、2464、3661、3390、8028、7769） |
| 🌊 汪洋大魚掃出 | 51 支 |
| 記憶海股票總數 | 51 支 |
| 猛虎等級（≥3次）| 10 支 |

---

## 📅 每日作業 SOP（半自動流程）

> 詳細作業表見 `每日作業SOP.html`

### 自動段（GitHub Actions 負責）
- 每週一～五 **20:39** 台灣時間，自動執行雷達掃描並推回 GitHub

### 人工段（Jeff 每日確認）
- **早盤前（08:30）**：開啟 `index/index.html` 查看前日掃描結果
- **盤中（09:00-13:30）**：按訊號操作，重點看猛虎池 + 汪洋大魚的「買入加碼」
- **收盤後（14:30）**：核對走勢，記錄結果
- **每週一次**：檢視魚池名單，評估是否調整個股

---

## 🔄 常見協作任務

1. **更新選股模型邏輯**（調整進出場條件、新增指標）
2. **維護魚池名單**（新增/移除個股，修改 `radar/radar.py` → `POOL_SETTINGS`）
3. **分析每日戰情資料**（解讀 `V7 daily json/plum_blossom_data.json`）
4. **升版 radar.py**（V7.x → V7.y，先在 `radar test/` 驗證）
5. **優化前端展示**（`index test/` 測試後合併至 `index/`）
6. **調整 GitHub Actions 排程**（修改 `auto radar yml/auto_radar.yml`）

---

## 📌 協作規範

- 版本號格式：`V[主版本].[次版本]`（目前為 **V7.4**）
- 新功能先在 `*test` 資料夾驗證，通過後升版至正式版
- `history/ocean_history.json` 僅追加，不刪除歷史記錄
- FinMind 快取檔 `finmind_cache.json` 與 `plum_blossom_data.json` 同目錄

---

## 🧠 Jeff 的操作偏好與背景

- 偏好**量化 + 籌碼面**雙重驗證
- 關注**三大法人動向**（外資、投信為主要訊號）
- 用語習慣：魚池、戰情室、彼夫有責、記憶海、梅花選股
- 工作語言：**繁體中文**
- 目標：打造可長期自動運作的選股機器，減少人工判斷

---

## 📝 版本更新日誌

| 日期 | 版本 | 說明 |
|---|---|---|
| 2026-04-26 | V7.3 | 新增 FinMind 股價前處理標準化函數、雙重火力補抓機制 |
| 2026-04-28 | V7.4 | 新增本地快取機制、API 精確計數器、粗篩量能門檻提升至 1,500 張 |
| 2026-04-28 | — | 資料夾重組（daily json / history / auto radar yml）、建立每日 SOP |
| 2026-05-01 | V7.5 | API 三劍客降載：① Yahoo MA5 前置預篩（攔截 65 支冗餘請求）② Yahoo 取代 FinMind 股價（市場掃描+魚池各省 1 call/股）③ TaiwanStockInfo 7 日獨立快取。實測 API 消耗：430 → 171 次（-60%）。Token 安全修復（env var）。 |

---

*此檔案由 Claude 與 Jeff 共同維護，請在每次重大協作後更新。*
