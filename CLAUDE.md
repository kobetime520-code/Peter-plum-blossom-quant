# 彼夫有責戰情室 — Claude 協作記憶檔

> 最後更新：2026-07-04
> 負責人：Jeff（kobetime520@gmail.com）

---

## 🎯 專案核心目標

建立一套台股**自動選股與監控系統**，以量化模型搭配三大法人籌碼，每日掃描股票池、輸出操作訊號，協助 Jeff 做出進出場決策。

---

## 📁 工作資料夾結構（2026-07-04 校正，檔案已集中至根目錄）

| 路徑 | 說明 |
|---|---|
| `radar.py` | 核心雷達掃描程式（正式版，根目錄） |
| `moly.py` / `git_sync.py` | 本地主算入口 / 精準推送（5 個戰報檔） |
| `plum_blossom_data.json` | 每日選股戰報（根目錄） |
| `ocean_history.json` | 記憶海（根目錄，僅追加） |
| `log_report.json` / `backtest_report.json` / `grace_theme_data.json` | 維運日誌 / 週回測 / Grace 題材 |
| `index.html` / `grace.html` / `mengong.html` | 前端展示頁面（根目錄） |
| `backtest_run.py` / `grace_run.py` / `mengong_auto.py` | 排程執行器（回測 / 題材 / 孟恭） |
| `finmind_cache.json` 等 `*_cache.json` | 本地快取（不推送） |
| `C:\Moly\`（倉庫外） | 排程進入點：`moly_start.ps1`（含交易日判斷）、`backtest_start.ps1`、`grace_start.ps1`、`holidays.txt`（證交所休市日）、`norton_root.pem` |
| `.github/workflows/manual_radar_update.yml` | GitHub Actions 手動備援（僅 workflow_dispatch，無 cron） |

---

## 🤖 自動排程（本機工作排程器，2026-07-04 新機移轉後）

> 架構為方案 B 本地主算：重度運算在本機執行，GitHub 僅展示戰報。排程任務設定為「使用者登入時執行」，排程時刻須保持開機且 User 帳號登入。

| 任務名稱 | 時間（台灣） | 執行內容 |
|---|---|---|
| `Moly-Daily` | 週一～五 20:39 | `C:\Moly\moly_start.ps1` → radar.py 掃描 + git_sync 推送 |
| `Moly-GraceDaily` | 每日 06:00 | `C:\Moly\grace_start.ps1` → grace_theme_gen.py 題材更新 |
| `Moly-BacktestWeekly` | 週六 06:00 | `C:\Moly\backtest_start.ps1` → backtest_generator.py 週回測 |
| `MengongAuto_Daily` | 每日 21:00 | `mengong_auto_run.bat` → 孟恭道路指引彙整（無需 API） |

手動備援：GitHub Actions 頁面觸發 `manual_radar_update.yml`（workflow_dispatch）。

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

### 自動段（本機工作排程器負責）
- 每週一～五 **20:39** 台灣時間，自動執行雷達掃描並推回 GitHub（另有每日 06:00 Grace、週六 06:00 回測、每日 21:00 孟恭）

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

- 版本號格式：`V[主版本].[次版本]`（目前為 **V9.0**）
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
| 2026-05-21 | V8.8 | PLAN F：量比第四關（≥1.2）；PLAN G-v2：3/5/8 趨勢品質（trend_quality）；PLAN H：前日低分股預篩快取（stock_result_cache.json，TTL 24h）；PLAN I：突破天數加分；PLAN J：猛虎池精銳上限 8 支；強勢評分納入趨勢品質加分。 |
| 2026-06-07 | V8.9 | 任務1：回測產生器 backtest_generator.py（5/30/126 勝率/報酬/超額，週六 06:00 排程）+ index 回測區塊復活；任務2：ATR×2 波動度動態停損（取代固定×0.9，護欄 -6%~-15%，新欄位 stop_loss_fixed/atr14/atr_pct/stop_loss_mode）；任務3：大盤環境過濾 ^TWII vs MA60 三段式（標記+縮倉+降權，_SCORE_FACTOR）；任務4：Grace 被動元件題材分頁 grace.html + grace_theme_gen.py（規則式本機產生，週日 07:00 排程）。新增排程 Moly-BacktestWeekly（週六）、Moly-GraceWeekly（週日）。 |
| 2026-07-04 | — | **排程健檢與補整**：① Grace 由誤植的週日 07:00 改回舊機實際規格**每日 06:00**（Moly-GraceDaily）② 補註冊 MengongAuto_Daily（每日 21:00，移轉時遺漏）③ 手動補跑本週六回測弭平空窗 ④ 資料夾結構與排程章節校正至現況（檔案已集中根目錄、排程改本機工作排程器）⑤ Python313 加入使用者 PATH。 |
| 2026-07-04 | — | **新機移轉完成**：Moly 排程由舊機（wangj）移轉至新機（User）。首測三輪通過（第三輪與 7/3 基準完全一致）。修復兩項新機環境問題：① Norton 防毒 SSL 攔截（truststore + sitecustomize.py 修 requests；Norton 根憑證附加 certifi 修 yfinance/curl_cffi，備份 `C:\Moly\norton_root.pem`，**certifi 升級後需重附加**）② 記憶海遭失敗測試洗空，已自 git 還原 7/3 狀態。重建 `C:\Moly\` 三支啟動腳本（moly/backtest/grace_start.ps1，UTF-8 BOM）+ `holidays.txt`（2026 下半年證交所休市日）。註冊排程：Moly-Daily（一~五 20:39）、Moly-BacktestWeekly（六 06:00）、Moly-GraceWeekly（日 07:00）。ps1 重導向改寫 `moly_ps.log` 避免 UTF-16 污染；舊 moly.log 歸檔為 `moly_legacy_20260704.log`。 |
| 2026-06-08 | V9.0 | 汪洋大魚選股階段一（零新增 API，僅作用於汪洋大魚入池）：A1 籌碼方向閘門（合計淨買超>0 外，須外資或投信至少一方同向買超，剔除「假合計正」）；A2 追高防護 RSI 上限三段式（多頭<80／中性<75／空頭<70）。market_regime 新增 rsi_ceiling 欄位；戰報新增兩道關卡攔截統計（yf_skipped_chip / yf_skipped_rsi）。 |
| 2026-07-04 | V9.1 UI | **index.html 排列優化 P1+P2**（Zoey 規劃，純前端、零 API 影響）：P1 資訊層級重排 — 區塊順序改為 Header→KPI→魚池導航→魚池主戰區→Dashboard→回測→公式橫幅→Moly 維運列；魚池順序改決策優先（猛虎→汪洋→黃金→爆發→永動→觀察→卡娃），由 `POOL_ORDER` 單一常數控制；導航列改 JS 依 POOL_ORDER 動態生成（根除與 displayOrder 順序漂移）；猛虎池預設展開；三張大型分頁入口卡縮為精簡按鈕列（`.subpage-nav`）。P2 池內排序升級 — sortStocks 新增「強勢評分」並設為預設；「買入加碼」卡片一律置頂（組內再依所選欄位排序）；排序選擇以 localStorage（`poolSort:魚池名`）跨日記憶。P3 卡片密度 — 新增「⚡ 緊湊列表」檢視切換（`viewMode` localStorage 記憶；一行一股：代碼｜股名｜現價｜評分｜籌碼｜動作；點列展開完整戰情卡；沿用產業族群／Tier 分組與排序邏輯；≤600px 自動隱藏籌碼欄）；卡片徽章雙列合併單列。P4 行動版動線 — 修復導航列 sticky 吸頂（V8.6 `position:relative` 圖層規則覆寫所致，抽離後恢復）；≤768px 分頁入口摺疊為 icon 圓鈕（title 保留全名）；行動版無 viewMode 記錄時預設緊湊列表（手動選擇優先）。 |

---

*此檔案由 Claude 與 Jeff 共同維護，請在每次重大協作後更新。*
