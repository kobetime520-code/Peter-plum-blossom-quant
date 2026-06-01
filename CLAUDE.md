# 彼夫有責戰情室 — Claude 協作記憶檔

> 最後更新：2026-05-17
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
| `radar/radar.py` | 核心雷達掃描程式（**彼夫有責戰情室 V8.7**，正式版） |
| `radar test/radar.py` | 雷達沙盒（V8.7，與正式版同步） |
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
| 🔥 姊夫爆發小魚池 | 短線爆發型股票（6155、3060、3236、1513、1519、1605） | 6 支 |
| 🍁 楓大永動魚池 | 穩定動能股（2308、00923、00910、2327、1785、2344、6485） | 7 支 |
| 🌟 彼神黃金魚池 | 核心精選股（3028、2484、3221、8182、8289、3042） | 6 支 |
| 🔭 測試員觀察水域 | 觀察中候選股（5289、5292、4749、6770、1711、8299、3673、3675） | 8 支 |
| 🐅 三日成猛虎水池 | 記憶海出現 ≥ 3 次自動晉升 | 動態 |
| 🌊 汪洋大魚 | 全市場掃描後符合三關篩選的強勢股（依強勢評分排序） | 動態 |

> 🐅 猛虎池條件：`history/ocean_history.json` 中出現次數 ≥ 3 次，自動加入

---

## ⚙️ 技術架構

### 資料來源
- **FinMind API**（主力精濾）：帳號 PeterJeff0226，綁定 kobetime520@gmail.com
- **Yahoo Finance yfinance**（全市場粗篩，批量下載每次 150 檔）

### V8.5 混合引擎流程
```
Yahoo Finance 全市場批量粗篩（chunk=150）
  ↓ 第一關：成交量 ≥ 2,000 張
  ↓ 第二關：收盤價 > MA30
  ↓ 第三關：收盤價 ≥ MA5（前置預篩，省 FinMind API）
FinMind 法人籌碼細部製卡
  ↓ 動作訊號判斷 + 強勢評分（0–100 分）
輸出至 plum_blossom_data.json（汪洋大魚依強勢評分排序）
```

### V8.5 核心功能
- **本地快取**：`finmind_cache.json` 避免重複呼叫 API
- **API 計數器**：`_api_calls_count` 精確計算（快取命中不計）
- **粗篩門檻**：成交量 ≥ **2,000 張**（縮圈戰術）
- **MA5 前置預篩**：收盤低於 MA5 直接攔截，大幅省 API
- **強勢評分**：三維度評分（技術面40+量能面25+籌碼面35=100分）
- **籌碼分級標籤**：chip_signal（雙買/投信單買/外資單買/無買）、inst_grade（S/A/B/C/X 級）

### 核心指標
- 收盤價（Close）、成交量（Volume，單位：張）
- MA5、MA10、MA30
- RSI14（14日RSI，Wilder平均法）
- vol_ratio（量比 = 當日量 / 5日均量）
- bull_align（多頭排列：MA5 > MA10 > MA30）
- 三大法人 30 日買賣超：`inst_buy`（合計）、`foreign_buy`（外資）、`trust_buy`（投信）
- 目標價 = 收盤 × 1.5、停損價 = 收盤 × 0.9

### 動作訊號邏輯
```python
action = "買入加碼" if close_price >= ma5 and inst_buy_30d > 0 else "靜候觀察"
```

### 強勢評分（strength_score，0–100 分）
汪洋大魚依此分數由高到低排序：

**技術面（最高 40 分）**
- 均線排列：多頭排列(MA5>MA10>MA30) +15 / MA5>MA30 +8 / 收盤>MA30 +3
- RSI 區間：50–70 +15 / 40–50 +8 / >70(超買) +5 / 30–40 +2
- 收盤偏離MA5：≥3% +10 / ≥1% +7 / ≥0% +4

**量能面（最高 25 分）**
- 量比：≥2.0 +15 / ≥1.5 +12 / ≥1.0 +8 / ≥0.7 +4
- 成交量：≥10000張 +10 / ≥5000張 +8 / ≥3000張 +6 / ≥2000張 +4

**籌碼面（最高 35 分）**
- 法人組合：外資+投信雙買 +15 / 投信單買 +10 / 外資單買 +7
- 強度等級：S級(≥5000張) +20 / A級(≥1000張) +15 / B級(≥500張) +10 / C級(>0張) +5

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

## 👥 Team Stock 成員 SKILL 索引

> SKILL 檔位置：`docs/05_Team_stock/[姓名]_SKILL.md`
> 呼叫方式：直接告訴 Claude「請用 Peter 身份」或「切換到 Eric 模式」即可啟動對應角色

### 指揮層

| 成員 | 職稱 | 核心任務 | SKILL 檔 |
|------|------|----------|----------|
| **Peter** | 投資執行長 & 策略長 | 戰略決策、KPI 監督、跨域協調，對 JW 負責 | `Peter_SKILL.md` |

### 運營層

| 成員 | 職稱 | 核心任務 | SKILL 檔 |
|------|------|----------|----------|
| **Maple** | 投資採購及財務長 | 資金管理、交易執行、成本控制 | `Maple_SKILL.md` |
| **Moly** | 投資排程營運長 | 本地排程（moly_start.bat）、radar.py 執行、Git 推送 | `Moly_SKILL.md` |
| **Right** | 投資研發長 | 量化架構設計、演算法優化、FinMind API 降載策略 | `Right_SKILL.md` |
| **Left** | 投資程設助理 | Git 版控、Bug 修復、index.html UI 調整（Right 的執行者） | `Left_SKILL.md` |
| **Zoey** | 投資行銷創意長 | Dashboard 2.0 視覺設計（Chart.js）、響應式 UI | `Zoey_SKILL.md` |

### 研究員團隊

| 成員 | 職稱 | 負責魚池 | 核心任務 | SKILL 檔 |
|------|------|----------|----------|----------|
| **Tim** | 基本面研究員 | 🍁楓大永動、🌟彼神黃金 | ROE/自由現金流/護城河評估（每季財報後） | `Tim_SKILL.md` |
| **Grace** | 題材面研究員 | 🔥姊夫爆發、🔭測試員觀察 | 市場熱點、產業趨勢、短線催化劑分析 | `Grace_SKILL.md` |
| **Joe** | 技術面研究員 | 🌊汪洋大魚、🐅三日猛虎 | MA5/MA30 趨勢判讀、停利×1.5/停損×0.9 | `Joe_SKILL.md` |
| **Eric** | 籌碼分析研究員 | 所有魚池（除汪洋大魚） | 三大法人買賣超、融資券比率預警 | `Eric_SKILL.md` |

### 魚池 × 成員對應速查

| 魚池 | 主責研究員 |
|------|-----------|
| 🔥 姊夫爆發小魚池 | Grace（題材）、Eric（籌碼） |
| 🍁 楓大永動魚池 | Tim（基本面）、Eric（籌碼） |
| 🌟 彼神黃金魚池 | Tim（基本面）、Eric（籌碼） |
| 🔭 測試員觀察水域 | Grace（題材）、Eric（籌碼） |
| 🐅 三日成猛虎水池 | Joe（技術）、Eric（籌碼） |
| 🌊 汪洋大魚 | Joe（技術）★ 唯一負責 |

### 🔌 已安裝 Skills（2026-05-25 新增）

| Skill | 路徑 | 主責成員 | 功能摘要 |
|---|---|---|---|
| `llm-cost-optimizer` | `skills/llm-cost-optimizer/SKILL.md` | Right | FinMind API 降載三劍客的系統化成本工程支援；目標 < 200 次/執行 |
| `karpathy-coder` | `skills/karpathy-coder/SKILL.md` | Left | 4 大 coding 原則（動手前先思考、簡單優先、外科手術修改、目標驅動）；commit 前品質守門 |
| `statistical-analyst` | `skills/statistical-analyst/SKILL.md` | Eric、Joe | 假設檢定、A/B 分析、樣本量計算；驗證選股訊號與指標改版效益 |
| `data-quality-auditor` | `skills/data-quality-auditor/SKILL.md` | Eric、Moly | 資料品質稽核（DQS 0–100）；每日確認 JSON 輸出格式健康度 |

### 溝通通則（全員適用）

- 禁止使用第一人稱（我、我的）與第二人稱（你、你的）
- 以「JW」或「使用者」稱呼對方
- 所有回應預設**繁體中文**

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

- 版本號格式：`V[主版本].[次版本]`（目前為 **V8.7**）
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
| 2026-05-14 | V8.5 | 新增 MA10、RSI14（Wilder法）、量比（vol_ratio）、多頭排列（bull_align）；新增三維度強勢評分（0–100分）；新增籌碼分級標籤（chip_signal / inst_grade）；量能粗篩門檻提升至 2,000 張；汪洋大魚依強勢評分排序。 |
| 2026-05-16 | — | 將 Team Stock 10 位成員 SKILL 索引正式套入 CLAUDE.md 工作室記憶（Peter/Maple/Moly/Right/Left/Zoey/Tim/Grace/Joe/Eric）。 |
| 2026-05-17 | V8.7 | PLAN C：MA5 突破日數追蹤（ma5_breakout_day / breakout_label / ma5_above_ma10_days）；PLAN A：甜蜜點三段式（HIGH/MID/LOW sweet_confidence）；PLAN B：題材標籤 15 大擴充 + 英文關鍵字 + yf_info 7 日快取（yf_info_cache.json）；Bug-01 修復：price_date 欄位補齊；移除回測績效報告 UI（V8.4 區塊，Magic lab 重設計中）；工作流程升級：Plan Mode → JW 授權 → 直接正式版（棄用沙盒）。 |

---

*此檔案由 Claude 與 Jeff 共同維護，請在每次重大協作後更新。*
