# 彼夫有責戰情室 — Claude 協作記憶檔

> 最後更新：2026-08-01
> 負責人：Jeff（kobetime520@gmail.com）
> 版本：**V9.2 ／ 前端 V9.2 UI**

---

## 📖 文件分工（單一事實來源）

| 文件 | 定位 |
|---|---|
| **`CLAUDE.md`（本檔）** | **規格唯一事實來源**：魚池設定、強勢評分、技術架構、排程、前端主題、版本日誌 |
| `README.md` | 對外簡介與導引，規格一律連回本檔，不重複載明 |
| `docs/00_INDEX.md` | 知識庫檔案位置索引；成員 SKILL 版本以各 SKILL 檔尾自述為準，索引不複製版本號 |
| `docs/05_Team_stock/*_SKILL.md` | 各成員角色設定正本（含自身版本宣告） |

> 規格若有異動，只改本檔；其他文件僅在「位置／連結」變動時才需同步。此規則於 2026-08-01（C1）建立，用以根除同一事實散在三處造成的漂移。

---

## 🎯 專案核心目標

建立一套台股**自動選股與監控系統**，以量化模型搭配三大法人籌碼，每日掃描股票池、輸出操作訊號，協助 Jeff 做出進出場決策。

---

## 📁 工作資料夾結構（2026-07-04 校正，檔案已集中至根目錄）

| 路徑 | 說明 |
|---|---|
| `radar.py` | 核心雷達掃描程式（正式版，根目錄） |
| `moly.py` / `git_sync.py` | 本地主算入口 / **全系統唯一推送實作**（預設 5 個戰報檔，可帶 files 參數；`.git_sync.lock` 互斥，2026-08-01 D1） |
| `log_setup.py` | 三支排程執行器共用的輪替 logger（單檔 2 MB、保留 3 份，2026-08-01 E1） |
| `plum_blossom_data.json` | 每日選股戰報（根目錄） |
| `ocean_history.json` | 記憶海（根目錄，**真·僅追加**，2026-08-01 A1 修正） |
| `log_report.json` / `backtest_report.json` / `grace_theme_data.json` | 維運日誌 / 週回測 / Grace 題材 |
| `push_status.json` | 推送狀態 sidecar（**本機專有、不進版控**，2026-08-01 E5；帶 `last_update` 供時效比對） |
| `index.html` / `grace.html` / `mengong.html` | 前端展示頁面（根目錄） |
| `backtest_run.py` / `grace_run.py` / `mengong_auto.py` | 排程執行器（回測 / 題材 / 孟恭） |
| `tests/` | 離線回歸測試（`run_all.py` 為批次入口；`manual_*.py` 需連網，不入批次，2026-08-01 D3） |
| `_archive/` | 已停用檔案歸檔（附 README 逐檔記錄停用原因，2026-08-01 E2）；**內容一律不要直接執行** |
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
| 🔥 姊夫爆發小魚池 | 短線精銳池（V9.2 起改動態篩選：inst_grade S/A + trend_quality STRONG/HEALTHY + MA5 突破 1~3 日，剔除金融/傳產，取 strength_score 前 8 檔；專屬停損停利 −7%/+8%） | 動態（≤8 支） |
| 🍁 楓大永動魚池 | 穩定動能股（2308、00923、00910、2327、1785、2344、6155） | 7 支 |
| 🌟 彼神黃金魚池 | 核心精選股（2484、3221、8182、8289、3042、3675） | 6 支 |
| 🔭 測試員觀察水域 | 觀察中候選股（5289、5292、4749、6770、8299、3673、5425、6224、3707、3016、5274、6270、6667、3706） | 14 支 |
| 🐅 三日成猛虎水池 | 記憶海出現 ≥ 3 次自動晉升（精銳上限 8 支，V8.8） | 動態（≤8 支） |
| 🌊 汪洋大魚 | 全市場掃描後通過四關粗篩 + A1／A2 雙閘門的強勢股（依強勢評分排序） | 動態 |
| 🃏 被動卡娃魚池 | **display-only 純展示**：被動元件觀察名單，分三層 Tier；不參與篩選、不影響猛虎池晉升、不計入儀表板多空／健康度統計 | 13 支 |

> 🐅 猛虎池條件：`ocean_history.json`（根目錄）中出現次數 ≥ 3 次，自動加入；該檔為**真·僅追加**，未命中股原樣保留（V9.2 / 2026-08-01 A1 修正）。
>
> 🃏 被動卡娃分層（`PASSIVE_KAWA_TIERS`）：**Tier 1 核心** 6173 信昌電、3026 禾伸堂、2492 華新科｜**Tier 2 主力** 6175 立敦、2472 立隆電、2327 國巨、2375 凱美、6449 鈺邦、8042 金山電、8163 達方｜**Tier 3 衛星** 3090 日電貿、3537 堡達、6432 今展科。
>
> 📍 名單正本在 `radar.py` 的 `POOL_SETTINGS` 與 `PASSIVE_KAWA_TIERS`；此表於 2026-08-01 對齊程式實況，日後改名單請同步兩處。

---

## ⚙️ 技術架構

### 資料來源
- **FinMind API**（主力精濾）：帳號 PeterJeff0226，綁定 kobetime520@gmail.com
- **Yahoo Finance yfinance**（全市場粗篩，批量下載每次 150 檔）

### 混合引擎流程（V8.5 骨幹 + V8.8 第四關 + V9.0 雙閘門）
```
Yahoo Finance 全市場批量粗篩（chunk=150）
  ↓ 第一關：成交量 ≥ 2,000 張
  ↓ 第二關：收盤價 > MA30
  ↓ 第三關：收盤價 ≥ MA5（前置預篩，省 FinMind API）
  ↓ 第四關：量比 ≥ 1.2（V8.8 縮圈）
FinMind 法人籌碼細部製卡
  ↓ A1 籌碼方向閘門：合計淨買超 > 0 外，須外資或投信至少一方同向買超（剔除假合計正，V9.0）
  ↓ A2 追高防護：RSI < 上限（多頭 80／中性 75／空頭 70，V9.0）
  ↓ 動作訊號判斷 + 強勢評分（0–100 分）+ ATR×2 動態停損（V8.9）
輸出至 plum_blossom_data.json（汪洋大魚依強勢評分排序）
```

> 🔥 姊夫爆發小魚池複用上述 market_pool 再做動態篩選（V9.2），零額外 API；該池套用專屬固定停損停利 −7%／+8%，不吃全局 ATR 動態停損。

### 核心功能
- **本地快取**：`finmind_cache.json` 避免重複呼叫 API
- **API 計數器**：`_api_calls_count` 精確計算（快取命中不計）
- **粗篩門檻**：成交量 ≥ **2,000 張**（縮圈戰術）
- **MA5 前置預篩**：收盤低於 MA5 直接攔截，大幅省 API
- **強勢評分**：三維度評分（技術面40+量能面25+籌碼面35=100分）
- **籌碼分級標籤**：chip_signal（雙買/投信單買/外資單買/無買）、inst_grade（S/A/B/C/X 級）

### 核心指標

| 指標 | 說明 |
|---|---|
| Close / Volume | 收盤價 / 成交量（單位：張） |
| MA5 / MA10 / MA30 | 移動平均線 |
| RSI14 | 14 日 RSI（Wilder 平均法） |
| vol_ratio | 量比 = 當日量 / 5 日均量 |
| bull_align | 多頭排列：MA5 > MA10 > MA30 |
| trend_quality | 3/5/8 趨勢品質（STRONG / HEALTHY / WATCH / WEAK，V8.8） |
| ma5_breakout_day | 站上 MA5 天數（V8.7；搭配 breakout_label、ma5_above_ma10_days） |
| inst_buy / foreign_buy / trust_buy | 三大法人 30 日買賣超（合計 / 外資 / 投信） |
| chip_signal / inst_grade | 籌碼分級標籤（雙買・投信單買・外資單買・無買 / S・A・B・C・X 級） |
| 目標價 | 收盤 × 1.5 |
| 停損價 | ATR×2 動態停損（護欄 −6%～−15%，V8.9 起取代固定 ×0.9；姊夫池另用 −7% 固定值） |

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

> 大盤環境過濾（V8.9）：^TWII vs MA60 三段式，空頭時以 `_SCORE_FACTOR` 對評分降權並縮倉。

---

## 🎨 前端主題（V9.2 UI）

| 主題 | 風格 | 說明 |
|---|---|---|
| 深海太空・極光玻璃版（Aurora Glass） | 預設 | 紫青極光漸層底 + 磨砂玻璃面板 + 星空層 |
| 粉紅泡泡糖・莓果馬卡龍版（Berry Macaron） | 可切換 | 淺色泡泡糖粉底 + 莓紅／薰衣草／蜜桃三色光暈，深莓文字（WCAG AA 全過），關閉星空層 |

> 右上角「🌸 切換粉紅泡泡糖版 ／ 🌌 切換極光玻璃版」按鈕切換（`[data-theme="light-ocean"]`）。分頁：`grace.html`（Grace 題材）、`mengong.html`（孟恭道路指引）、`warroom.html`、`stellar_blueprint.html`。

---

## 📊 最新戰情快照（2026-08-01 16:45）

> ⚠️ 此表為人工留痕，**不是即時值**。即時數據一律以 `log_report.json`（維運）與 `plum_blossom_data.json`（戰報）為準，或直接開 `index.html`。

| 項目 | 數值 |
|---|---|
| 最後更新時間 | 2026/08/01 16:45（A3 補跑 7/31 空窗） |
| FinMind API 消耗 | 64 次（處理 65 檔、快取命中 10） |
| 大盤環境 | 🔴 空頭（加權 43,119.75 vs MA60 44,089.08，乖離 −2.2%，score_factor 0.85、rsi_ceiling 70） |
| 🐅 猛虎池活躍股 | 8 支（滿編，全數「買入加碼」） |
| 🌊 汪洋大魚掃出 | 16 支 |
| 記憶海股票總數 | 246 支（真·僅追加生效後） |
| 猛虎等級（≥3 次） | 70 支（經精銳上限取前 8 支入池） |

---

## 📅 每日作業 SOP（半自動流程）

### 自動段（本機工作排程器負責）
- 每週一～五 **20:39** 台灣時間，自動執行雷達掃描並推回 GitHub（另有每日 06:00 Grace、週六 06:00 回測、每日 21:00 孟恭）
- 執行狀態可用 `排程進度看板.bat`（或 `schedule_progress.ps1 -Watch`）查看

### 人工段（Jeff 每日確認）
- **早盤前（08:30）**：開啟 `index.html` 查看前日掃描結果
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
| **Moly** | 投資排程營運長 | 本地排程（`C:\Moly\moly_start.ps1`）、radar.py 執行、Git 推送 | `Moly_SKILL.md` |
| **Right** | 投資研發長 | 量化架構設計、演算法優化、FinMind API 降載策略 | `Right_SKILL.md` |
| **Left** | 投資程設助理 | Git 版控、Bug 修復、index.html UI 調整（Right 的執行者） | `Left_SKILL.md` |
| **Zoey** | 投資行銷創意長 | Dashboard 2.0 視覺設計（Chart.js）、響應式 UI | `Zoey_SKILL.md` |

### 研究員團隊

| 成員 | 職稱 | 負責魚池 | 核心任務 | SKILL 檔 |
|------|------|----------|----------|----------|
| **Tim** | 基本面研究員 | 🍁楓大永動、🌟彼神黃金 | ROE/自由現金流/護城河評估（每季財報後） | `Tim_SKILL.md` |
| **Grace** | 題材面研究員 | 🔥姊夫爆發、🔭測試員觀察 | 市場熱點、產業趨勢、短線催化劑分析 | `Grace_SKILL.md` |
| **Joe** | 技術面研究員 | 🌊汪洋大魚、🐅三日猛虎 | MA5/MA30 趨勢判讀、停利×1.5／ATR×2 動態停損 | `Joe_SKILL.md` |
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
| 🃏 被動卡娃魚池 | Grace（被動元件題材，對應 `grace.html`）★ 純展示池，不進篩選 |

### 🔌 已安裝 Skills（2026-05-25 新增）

> 安裝位置為工作區全域目錄 `C:\AIworkplace\.claude\skills\[skill 名]\SKILL.md`（非本 repo 內的 `skills/`）。

| Skill | 主責成員 | 功能摘要 |
|---|---|---|
| `llm-cost-optimizer` | Right | FinMind API 降載三劍客的系統化成本工程支援；目標 < 200 次/執行 |
| `karpathy-coder` | Left | 4 大 coding 原則（動手前先思考、簡單優先、外科手術修改、目標驅動）；commit 前品質守門 |
| `statistical-analyst` | Eric、Joe | 假設檢定、A/B 分析、樣本量計算；驗證選股訊號與指標改版效益 |
| `data-quality-auditor` | Eric、Moly | 資料品質稽核（DQS 0–100）；每日確認 JSON 輸出格式健康度 |
| `pdf` / `xlsx` / `deep-research`（內建） | Tim | 基本面健檢工具鏈：PDF 財報抽取／OCR、Excel 健檢追蹤表、護城河多來源交叉驗證（詳見 `docs/05_Team_stock/Tim_SKILL.md`「可用 Skills 清單」） |

### 溝通通則（全員適用）

- 禁止使用第一人稱（我、我的）與第二人稱（你、你的）
- 以「JW」或「使用者」稱呼對方
- 所有回應預設**繁體中文**

---

## 🔄 常見協作任務

1. **更新選股模型邏輯**（調整進出場條件、新增指標 → `radar.py`）
2. **維護魚池名單**（新增/移除個股，修改 `radar.py` → `POOL_SETTINGS`；被動卡娃池為 `PASSIVE_KAWA_TIERS`）
3. **分析每日戰情資料**（解讀 `plum_blossom_data.json`）
4. **升版 radar.py**（V9.x → V9.y，Plan Mode 規劃 → JW 授權 → 直接改正式版）
5. **優化前端展示**（直接改 `index.html`／`grace.html`／`mengong.html`）
6. **維護手動備援**（`.github/workflows/manual_radar_update.yml`，僅 `workflow_dispatch`）
7. **排查排程異常**（`排程進度看板.bat`／`moly_ps.log`／`radar_run.log`）
8. **跑回歸測試**（改動 `radar.py` 閘門邏輯後執行 `python tests/run_all.py`，全離線、零 API）
9. **手動補推**（`python git_sync.py`＝5 個戰報檔；`python git_sync.py <檔名>`＝指定檔案）

---

## 📌 協作規範

- 版本號格式：`V[主版本].[次版本]`（目前為 **V9.2**，前端 **V9.2 UI**）
- 工作流程：**Plan Mode 規劃 → JW 授權 → 直接改正式版**（沙盒資料夾 `radar test/`、`index test/` 已於 2026-05-17 廢止並移除）
- 規格文件單一事實來源為本檔，`README.md` 與 `docs/00_INDEX.md` 只作導引（見「📖 文件分工」）
- `ocean_history.json`（根目錄）**真·僅追加**：以既有累計為基底，當日未命中股原樣保留；筆數縮水即不覆寫
- **推送一律走 `git_sync.py`**（2026-08-01 D1 收斂後為唯一實作），勿在任何腳本內自行 `git add/commit/push`——會繞過 stash 防呆、rebase 衝突處理、推送重試與 `.git_sync.lock` 互斥，重蹈孟恭旁路的覆轍
- **改動 `radar.py` 閘門邏輯後須跑 `python tests/run_all.py`**（離線、零 API），並視情況補測試
- 程式、戰報、快取、前端頁面位於**專案根目錄**（2026-07-04 起集中）；例外為 `tests/`（回歸測試）與 `_archive/`（停用檔歸檔），皆 2026-08-01 建立
- FinMind API token 以環境變數傳入，不寫入程式碼；日誌目前仍會落明文 token（**JW 決議接受風險、不處置**，自保方式為日誌不外傳）

---

## 🧠 Jeff 的操作偏好與背景

- 偏好**量化 + 籌碼面**雙重驗證
- 關注**三大法人動向**（外資、投信為主要訊號）
- 用語習慣：魚池、戰情室、彼夫有責、記憶海、梅花選股
- 工作語言：**繁體中文**
- 目標：打造可長期自動運作的選股機器，減少人工判斷

---

## 📝 版本更新日誌

> 依日期**降序**排列（最新在最上）；同日多筆依當日執行先後排列。新增紀錄請放在對應日期的位置，勿追加到表尾。

| 日期 | 版本 | 說明 |
|---|---|---|
| 2026-08-01 | — | **記憶海僅追加修正與回補（稽核 A1／A2／A3，對應發現 F-01／F-02）**：① **A1**（`244b1ca`）`new_history` 改以既有累計正規化複製為基底，只更新命中股的 `count`／`last_date`，未命中者原樣保留；向下相容（V6 純 int）改為對整份歷史生效；防清空護欄由「當日 0 檔才保留」升級為「**筆數縮水即不覆寫**」。猛虎晉升觸發範圍刻意維持只從當日命中股，避免拉入無當日股價個股觸發雙重火力補抓、推高 API。27 項離線斷言全過。② **A2**（`a8584b8`）記憶海回補採 W4 窗口（V9.2 上線 07-07～07-30，18 個掃描日），3 支 → 241 支；不採全歷史（80 天窗口 870 支中 671 支達 count≥3＝77%，門檻等同失效），W4 為 28% 仍具鑑別度；回放排除 7 筆非掃描 commit，7/10 由誤採的重建檔 56 支修正回當日實際 34 支。③ **A3**（`6f5a424`）補跑 7/31 空窗：以 `FORCE_RUN=true` 走完整生產路徑，12 分 15 秒、API 64 次、`push_status OK`。生產驗證：當日命中 16 支，舊邏輯會把記憶海砍到 16 支，實際 241 → **246 支**，count≥3 者 68 → 70 支，猛虎池 0 → **8 支滿編且全數「買入加碼」**。④ F-02 根因更正：非 DNS 中斷，而是**掃描中途機器重啟**（`0x40010004` DBG_TERMINATE_PROCESS，事件記錄 20:51:29 關機／20:51:55 開機），與 7/10 的 `0xC000013A` 同屬「掃描執行中機器被關掉」，程式面無法防堵（殘留風險）。 |
| 2026-08-01 | — | **文件單一事實來源建立（稽核 C1，對應發現 F-06／F-04）**：魚池設定、強勢評分、技術架構、排程、前端主題五段規格集中於本檔，新增「📖 文件分工」章節載明規則；`README.md` 刪除上述重複段落，改為簡介＋導引＋連回本檔；`docs/00_INDEX.md` 移除成員 SKILL 版本號硬編欄位，改以「版本以各 SKILL 檔尾自述為準」指向正本，根除索引與檔案版本漂移。併入 README 專有且較新的事實：流程圖補第四關量比與 A1／A2 雙閘門、核心指標改表格並補 trend_quality／ma5_breakout_day、停損價由過期的「收盤 × 0.9」更正為 ATR×2 動態停損、猛虎池補精銳上限 8 支、記憶海路徑由 `history/ocean_history.json` 更正為根目錄、新增前端雙主題章節。 |
| 2026-08-01 | — | **版本日誌重排與過期路徑校正（稽核 C3，對應發現 F-07／F-08）**：① 版本日誌表由亂序（6 月與 7 月交錯、07-09 排在 07-10 之後）改為**依日期降序**，同日多筆依當日執行先後排列；② 「常見協作任務」路徑校正至根目錄（`radar/radar.py`→`radar.py`、`V7 daily json/`→根目錄、`auto radar yml/auto_radar.yml`→`.github/workflows/manual_radar_update.yml`），並補「維護手動備援」「排查排程異常」兩項；③ 「協作規範」移除已廢止的 `*test` 沙盒流程敘述，改載明 Plan Mode → JW 授權 → 直接正式版，記憶海路徑與真·僅追加語意同步；④ 每日 SOP 移除不存在的 `每日作業SOP.html` 引用、`index/index.html`→`index.html`、補排程看板；⑤ 「最新戰情快照」由 2026-04-28 更新至 08-01 實測值並註明非即時值；⑥ 成員索引 Moly 的 `moly_start.bat` 改為 `C:\Moly\moly_start.ps1`、Joe 的「停損×0.9」改為 ATR×2 動態停損。 |
| 2026-08-01 | — | **魚池表對齊 radar.py 實況**（C3 施工中發現的新漂移，F-06 殘留；以程式為準）：🍁 楓大永動 `6485` → **`6155`**；🌟 彼神黃金移除 `3028`、補 `3675`；🔭 測試員觀察由 8 支修正為**實際 14 支**（移除 `1711`／`3675`，補 `5425`、`6224`、`3707`、`3016`、`5274`、`6270`、`6667`、`3706`）；補列文件從未記載的 **🃏 被動卡娃魚池**（`PASSIVE_KAWA_TIERS`，display-only 13 支，分 Tier 1 核心／Tier 2 主力／Tier 3 衛星，不參與篩選、不影響猛虎晉升、不計入多空統計），並加入魚池 × 成員速查表。表下加註「名單正本在 `radar.py`，改名單須同步兩處」。 |
| 2026-08-01 | — | **啟動橫幅版本號同步（稽核 C4，對應發現 F-05）**：`radar.py` 啟動橫幅長期停在 V8.9（未列 V9.0 雙閘門與 V9.2 姊夫池動態引擎），導致日誌／看板無法據以判斷執行版本。修法不只改字串，另新增模組常數 `RADAR_VERSION`／`RADAR_VERSION_NOTE` 集中管理，啟動橫幅與完成訊息（原「V8.9 儀表板數據」）改引用同一常數，升版只需改一行，根除「兩處各自寫死而落後」的復發路徑。檔頭註解原已為 V9.2，無須更動。已過 `py_compile` 與橫幅實際輸出驗證。 |
| 2026-08-01 | — | **推送流程收斂 + push_status 移出戰報檔（稽核 D1／E5，對應發現 F-09／F-15）**：兩項合併處理，因為 E5 使 `log_report.json` 恆為 dirty、逼 `git_sync` 每次都走 stash／pull／pop，而 D1 的旁路又在同一時間窗競用 repo。① **D1**：`mengong_auto.py` 移除自帶的 `git add/commit/push`，改呼叫 `git_sync.sync_to_github(files=..., commit_msg=...)`；`git_sync` 參數化（V1.2 → V1.3）並新增 `.git_sync.lock` 互斥鎖（等待上限 180 秒、陳舊鎖 10 分鐘自動回收），孟恭 21:00 與 radar 20:39～21:25 的時間窗重疊改為明確排隊；衝突處理的 `checkout --theirs` 目標改為本次傳入的檔案，不再寫死 `SYNC_FILES`。**推送時機不變**，孟恭資料仍於 21:00 當下上線（若改採「只產檔、交給白名單」會延到隔天、週末不上線，故不採）。② **E5**：`push_status` 原本在 `git_sync` 提交「之後」才回寫 `log_report.json`，使 GitHub 上的值永遠慢一輪，且工作區每次執行後恆為 dirty。實測 `index.html` **未讀此欄位**，讀取者僅 `moly.py`／`schedule_progress.ps1`／`tests/verify_v89.py` 三個本機端，故整欄移至 `push_status.json`（gitignored），並帶 `last_update` 供時效比對；`moly.py` 讀取失敗不再樂觀回傳 OK，改回 `UNKNOWN` 觸發告警。③ 順帶修復 `git_sync` 的無變更誤判：工作區有其他未暫存變動時 git 回「no changes added to commit」而非「nothing to commit」，舊字串比對漏接會把無變更誤判為推送失敗；改以 `git diff --cached --quiet` 明確判定。此瑕疵原被 `log_report.json` 恆 dirty 遮蔽，E5 讓工作區恢復乾淨後才會踩到。驗證：推送鎖三情境實測、無變更路徑回傳 True 不產生 commit、`push_status` 四種偵測路徑（正常／非本輪殘留／FAILED／檔案不存在）全對。 |
| 2026-08-01 | — | **建立 `tests/` 並補 V9.x 閘門離線回歸測試（稽核 D3，對應發現 F-11）**：三支測試腳本原散在根目錄且被 `.gitignore` 逐檔排除，V9.0～V9.2 的四道新閘門完全沒有版控中的自動化保護。① 建立 `tests/` 納入版控，既有三支移入並依是否需連網分流（`manual_atr_stop.py`／`manual_market_regime.py` 需 yfinance，不入批次；`verify_v89.py` 離線，補 `chdir` 修正相對路徑）；② 新增 `tests/test_gates.py`（**57 項離線斷言**，零 API、零網路）涵蓋 A1 籌碼方向閘門、A2 追高防護、記憶海真·僅追加與防縮水護欄、姊夫池動態篩選與排序、−7%／+8% 停損停利、融資閘門容錯放行、大盤三段式與 `rsi_ceiling`；③ 新增 `tests/run_all.py` 批次入口。為使最高風險邏輯可測，將兩段 inline 碼**原地抽為純函式（判斷條件一字未改）**：`_passes_ocean_gates(s_data, rsi_ceiling)` 與 `merge_ocean_history(history, hits, today)`。抽取等價性以 25,000 組隨機輸入對「抽取前原始碼逐字重現版」比對，**差異 0 筆**。 |
| 2026-08-01 | — | **日誌自動輪替（稽核 E1，對應發現 F-12）**：`moly.py`／`grace_run.py`／`backtest_run.py` 三支排程執行器各自以 `FileHandler(mode='a')` 寫同一支 `moly.log`，完全沒有輪替、只能單向成長；過去兩次歸檔（07-04、07-09）都是編碼修復時順手做的人工動作。新增 `log_setup.py`（`RotatingFileHandler`，單檔 2 MB、保留 3 份、`delay=True`），三支共用同一份設定避免再度漂移；`mengong_auto_run.bat` 另加大小檢查（該日誌由 `.bat` 的 `>>` 重導產生、檔案由 cmd 持有，Python 端無法輪替），並以子程序取得檔案大小，避開「在 `if` 區塊內取用同區塊剛設定的變數」需延遲展開的 batch 陷阱。**不在此次範圍**：`moly_ps.log` 由倉庫外的 `C:\Moly\moly_start.ps1` 重導產生，另案處理。已知限制：週六 06:00 兩支排程同時觸發、同寫 `moly.log`，Windows 檔案鎖可能使該次 rollover 失敗（僅影響輪替，不影響寫入）。 |
| 2026-08-01 | — | **停用檔歸檔與殘留清理（稽核 E2／E3，對應發現 F-13）**：建立 `_archive/` 並附 README 逐檔記錄停用原因，**一律 `git mv`、不做實體刪除**。歸檔 8 檔：`moly_start.bat`（已被 `C:\Moly\moly_start.ps1` 取代，且無交易日判斷、誤用會在假日產出無效戰報）、`mengong_summary.py`（功能已併入 `mengong_auto.py`）、`setup_mengong_schedule.bat`、`MengongAuto_Daily.xml`、兩支 legacy log、`institutional_investors_test.csv`（`finmind_gateway testing/` 唯一殘留檔，實測為**未追蹤**而非稽核所載的已追蹤，父層兩級空殼目錄一併移除）、`yongguang_transcript.txt`。清除殘留：`docs/05_Team_stock/晨報/desktop.ini`（`git rm --cached`＋移除空目錄）、`__pycache__/`、`.claude/worktrees/`（`git worktree list` 確認未註冊、0 檔案）。連帶修正引用：`mengong.html` 五處 `mengong_summary.py` 文案、`Moly_SKILL.md` 兩處殘留的 `moly_start.bat`（C3 當時只改到本檔成員索引，SKILL 正本仍是舊值）。 |
| 2026-08-01 | — | **Zoey 雙 SKILL 明確分工＋凍結資料標註（稽核 D2／E4，對應發現 F-10／F-14）**：① **D2**：Zoey 兩份 SKILL **刻意不合併** —— `Zoey_SKILL.md` 是角色人格正本（誰在做、以什麼立場做），`Zoey_war-room-designer_SKILL.md` 是視覺設計方法論工具包（用什麼流程做）且已獨立安裝為全域 skill（`C:\AIworkplace\.claude\skills\war-room-designer\`），合併會破壞該安裝。兩檔檔首互指並各自載明觸發條件，`docs/00_INDEX.md` 補說明；同時校正工具包內落後的 V9.1 字串 4 處為 V9.2 UI 雙主題並**同步全域安裝副本**（本次漂移正是兩邊未同步所致，故加註「修改後須同步副本」）。② **E4**：兩份已凍結的手動資料前端仍當現行資料呈現 —— `grace.html` 個股轉型深度專題取既有 `last_updated`（2026-06-27）、`mengong.html` 歷史航跡典藏庫因陣列無 metadata 改取資料中最新 `date`（2026.05.23），皆標示「手動維護 · 資料截至 …（不隨排程更新）」。兩頁以瀏覽器實測渲染正確、無 console 錯誤。 |
| 2026-07-13 | V9.2 UI | **粉色海洋版換膚「粉紅泡泡糖・莓果馬卡龍」**（Zoey 配色，純前端、零 API 影響，僅動 `[data-theme="light-ocean"]` 變數與連動處，極光玻璃版與版面邏輯不變）：背景由 V9.2「深藍夜幕底」改為淺色泡泡糖粉底（`linear-gradient #FFF0F6→#FFD6E7→#F4A6C8` ＋莓紅／薰衣草／蜜桃三色 radial 光暈）；文字改深色系確保淺底可讀 — `--text-main #4B1528`（對比 12.94）、`--text-muted #993556`（6.20）；主強調 `--neon-cyan #B83A63`（莓粉，4.85）、`--neon-gold #8A5807`（深金，5.33）皆加深至過 WCAG AA 4.5（含 12px 小字）；買入綠 `#3B6D11`（5.50）／停損紅 `#C0392B`（4.82）語意色保留；面板改白粉半透明玻璃感；淺底關閉星空層 `body::before`（白星點不可見）；neon-cyan 加深後 `.version-badge`／active nav 徽章改白字維持對比。同步更新切換鈕文字「🌸 切換粉紅泡泡糖版」與 V9.2 UI 說明。全數對比度以程式化計算＋新建元素套變數實測確認（AA 全過）。 |
| 2026-07-11 | — | **名冊與 SKILL 版本同步稽核**（29 位 agent 全數註冊正常、16 個 skill 掛載正常）：Team Stock 5 人 SKILL 對齊 V9.2 — Eric V1.3（姊夫池融資 10 日遽增風控閘門）、Right V2.3（姊夫池動態篩選架構）、Joe V2.4（姊夫池專屬停損停利 −7%/+8% + suggested_position）、Zoey V2.4（V9.2 UI 極光玻璃／泡泡糖波浪雙主題，修正檔內 V8.9 徽章殘留）、Left V2.4（V9.2 UI 雙主題維護）；Tim V2.2 footer 補記名單同步日期（2026-07-11）；`.claude\agents\` 對應 5 檔版本宣告同步；本檔魚池表姊夫池改動態篩選描述、協作規範版本更新至 V9.2。 |
| 2026-07-10 | — | **Moly-Daily 失敗排查 + 記憶海防清空護欄**：① 排程 20:39 失敗排查：回傳碼 0xC000013A（外部強制終止，非程式錯誤；同時段 nordsec-threatprotection-service 異常終止 2 次為最可疑源），手動重跑 radar.py 完整成功不可重現，戰報以手動重跑弭平 ② 定位記憶海清空根因：7/9 汪洋大魚合法掃出 0 支 → radar.py `new_history` 僅保留今日出現股票 → 整檔被 `{}` 覆寫（7/4 SSL 事件洗空為同一機制），與「僅追加」設計矛盾 ③ radar.py 加防清空護欄：汪洋 0 支時保留舊記憶海不覆寫 ④ 記憶海資料修復：以 7/8 版本(d7ca0aa)為基準套用今日掃描合併重建（56 支，count≥3 猛虎候選 7 支：1909=6、1216/2889/4114/2637=4、2369/2601=3）⑤ **看板即時進度來源修正**：radar.py 的 stdout 由 moly.py 導向 `radar_run.log`（非 `moly_ps.log`，後者僅含 logger 與 git_sync 輸出），看板執行中改讀前者；moly.py 子程序環境加 `PYTHONUNBUFFERED=1`（實測：未設時執行中檔案為 0 bytes、8KB 區塊緩衝至結束才 flush，故看板看不到逐批進度，且行程遭強制終止時輸出全失 — 這正是今日 radar_run.log 為 0 bytes 的原因，該檔無法用於判定死亡時點）。 |
| 2026-07-09 | — | **排程進度看板 + 日誌編碼修復**：① 新增 `schedule_progress.ps1`（前景終端機看板：四排程狀態／戰報檔新鮮度／log_report 摘要／日誌尾行；`-Watch` 即時刷新、Ctrl+C 離開）與 `排程進度看板.bat`（雙擊啟動，非背景作業）② 修復 `C:\Moly\` 三支啟動腳本（moly/grace/backtest_start.ps1）`*>>` 重導向編碼：Python 輸出前加 `[Console]::OutputEncoding=UTF8`，中文不再於寫檔前經 CP950 損毀（修復後 `moly_ps.log` 為 UTF-16 LE 含 BOM，讀取靠 BOM 自動偵測）③ 受損舊檔歸檔 `moly_ps_legacy_20260709.log` ④ 看板日誌雙軌（2026-07-10 修正即時來源為 `radar_run.log`，見下列）；孟恭監看目標為 `mengong_summary.json`。 |
| 2026-07-07 | V9.2 | **姊夫爆發小魚池改造**（Right架構+Joe停損停利+Eric籌碼閘門，短線精銳池）：固定5檔清單 → 動態篩選（`_select_jiefu_pool`，複用汪洋大魚 market_pool，零額外API）：inst_grade S/A（法人30日買超≥1000）+ trend_quality STRONG/HEALTHY（趨勢向上）+ ma5_breakout_day 1~3日（剛站上均線）+ 剔除金融/傳產（`JIEFU_EXCLUDED_INDUSTRIES`），取strength_score前8檔。停損停利改專屬固定 -7%/+8%（`_apply_jiefu_risk_params`，取代全局ATR動態停損，僅作用此池）；新增建議部位欄位 `suggested_position`（10萬本金、單筆2%曝險反推，固定約2.9萬）；新增融資10日遽增風控閘門 `_check_margin_not_surging`（FinMind `TaiwanStockMarginPurchaseShortSale`，增幅≥30%剔除，無資料/API異常預設放行不誤殺）。董監持股：評估 wespai（stock.wespai.com/pick）爬蟲整合，因robots.txt缺失、頁面穩定性未驗證，**JW決議暫緩**，改留 `director_holding_note` 人工複核提示欄位。已通過 `py_compile` 與10項離線邏輯自測（閘門/排序/防禦性容錯）。 |
| 2026-07-06 | — | **Tim SKILL 升 V2.2 + Skills 綁定**：Tim_SKILL.md 新增「可用 Skills 清單」章節（核心：pdf/xlsx/deep-research；進階：pulse/docx/metrics-review；附使用原則）；「已安裝 Skills」表補列 Tim 基本面健檢工具鏈，專案記憶檔留痕。 |
| 2026-07-05 | — | **Team Stock 7 人 SKILL 升版**（對齊 V9.0/V9.1 + 新增工作連結章節）：Right V2.2（A1/A2 雙閘門+大盤環境過濾）、Joe V2.3（ATR×2 動態停損+A2 RSI 上限）、Eric V1.2（A1 籌碼方向閘門）、Grace V2.4（grace.html 題材分頁工作流）、Left V2.3（+grace 分頁、根目錄路徑、V9.1 UI 實作紀錄）、Zoey V2.3（V9.1 P1–P4 排列優化規劃）、Moly V2.2（新機移轉、四項排程、Norton SSL 維運知識）。每份 SKILL 新增「工作連結」表，綁定成員專業與實際檔案路徑。 |
| 2026-07-04 | — | **排程健檢與補整**：① Grace 由誤植的週日 07:00 改回舊機實際規格**每日 06:00**（Moly-GraceDaily）② 補註冊 MengongAuto_Daily（每日 21:00，移轉時遺漏）③ 手動補跑本週六回測弭平空窗 ④ 資料夾結構與排程章節校正至現況（檔案已集中根目錄、排程改本機工作排程器）⑤ Python313 加入使用者 PATH。 |
| 2026-07-04 | — | **新機移轉完成**：Moly 排程由舊機（wangj）移轉至新機（User）。首測三輪通過（第三輪與 7/3 基準完全一致）。修復兩項新機環境問題：① Norton 防毒 SSL 攔截（truststore + sitecustomize.py 修 requests；Norton 根憑證附加 certifi 修 yfinance/curl_cffi，備份 `C:\Moly\norton_root.pem`，**certifi 升級後需重附加**）② 記憶海遭失敗測試洗空，已自 git 還原 7/3 狀態。重建 `C:\Moly\` 三支啟動腳本（moly/backtest/grace_start.ps1，UTF-8 BOM）+ `holidays.txt`（2026 下半年證交所休市日）。註冊排程：Moly-Daily（一~五 20:39）、Moly-BacktestWeekly（六 06:00）、Moly-GraceWeekly（日 07:00）。ps1 重導向改寫 `moly_ps.log` 避免 UTF-16 污染；舊 moly.log 歸檔為 `moly_legacy_20260704.log`。 |
| 2026-07-04 | V9.1 UI | **index.html 排列優化 P1+P2**（Zoey 規劃，純前端、零 API 影響）：P1 資訊層級重排 — 區塊順序改為 Header→KPI→魚池導航→魚池主戰區→Dashboard→回測→公式橫幅→Moly 維運列；魚池順序改決策優先（猛虎→汪洋→黃金→爆發→永動→觀察→卡娃），由 `POOL_ORDER` 單一常數控制；導航列改 JS 依 POOL_ORDER 動態生成（根除與 displayOrder 順序漂移）；猛虎池預設展開；三張大型分頁入口卡縮為精簡按鈕列（`.subpage-nav`）。P2 池內排序升級 — sortStocks 新增「強勢評分」並設為預設；「買入加碼」卡片一律置頂（組內再依所選欄位排序）；排序選擇以 localStorage（`poolSort:魚池名`）跨日記憶。P3 卡片密度 — 新增「⚡ 緊湊列表」檢視切換（`viewMode` localStorage 記憶；一行一股：代碼｜股名｜現價｜評分｜籌碼｜動作；點列展開完整戰情卡；沿用產業族群／Tier 分組與排序邏輯；≤600px 自動隱藏籌碼欄）；卡片徽章雙列合併單列。P4 行動版動線 — 修復導航列 sticky 吸頂（V8.6 `position:relative` 圖層規則覆寫所致，抽離後恢復）；≤768px 分頁入口摺疊為 icon 圓鈕（title 保留全名）；行動版無 viewMode 記錄時預設緊湊列表（手動選擇優先）。 |
| 2026-06-08 | V9.0 | 汪洋大魚選股階段一（零新增 API，僅作用於汪洋大魚入池）：A1 籌碼方向閘門（合計淨買超>0 外，須外資或投信至少一方同向買超，剔除「假合計正」）；A2 追高防護 RSI 上限三段式（多頭<80／中性<75／空頭<70）。market_regime 新增 rsi_ceiling 欄位；戰報新增兩道關卡攔截統計（yf_skipped_chip / yf_skipped_rsi）。 |
| 2026-06-07 | V8.9 | 任務1：回測產生器 backtest_generator.py（5/30/126 勝率/報酬/超額，週六 06:00 排程）+ index 回測區塊復活；任務2：ATR×2 波動度動態停損（取代固定×0.9，護欄 -6%~-15%，新欄位 stop_loss_fixed/atr14/atr_pct/stop_loss_mode）；任務3：大盤環境過濾 ^TWII vs MA60 三段式（標記+縮倉+降權，_SCORE_FACTOR）；任務4：Grace 被動元件題材分頁 grace.html + grace_theme_gen.py（規則式本機產生，週日 07:00 排程）。新增排程 Moly-BacktestWeekly（週六）、Moly-GraceWeekly（週日）。 |
| 2026-05-21 | V8.8 | PLAN F：量比第四關（≥1.2）；PLAN G-v2：3/5/8 趨勢品質（trend_quality）；PLAN H：前日低分股預篩快取（stock_result_cache.json，TTL 24h）；PLAN I：突破天數加分；PLAN J：猛虎池精銳上限 8 支；強勢評分納入趨勢品質加分。 |
| 2026-05-17 | V8.7 | PLAN C：MA5 突破日數追蹤（ma5_breakout_day / breakout_label / ma5_above_ma10_days）；PLAN A：甜蜜點三段式（HIGH/MID/LOW sweet_confidence）；PLAN B：題材標籤 15 大擴充 + 英文關鍵字 + yf_info 7 日快取（yf_info_cache.json）；Bug-01 修復：price_date 欄位補齊；移除回測績效報告 UI（V8.4 區塊，Magic lab 重設計中）；工作流程升級：Plan Mode → JW 授權 → 直接正式版（棄用沙盒）。 |
| 2026-05-16 | — | 將 Team Stock 10 位成員 SKILL 索引正式套入 CLAUDE.md 工作室記憶（Peter/Maple/Moly/Right/Left/Zoey/Tim/Grace/Joe/Eric）。 |
| 2026-05-14 | V8.5 | 新增 MA10、RSI14（Wilder法）、量比（vol_ratio）、多頭排列（bull_align）；新增三維度強勢評分（0–100分）；新增籌碼分級標籤（chip_signal / inst_grade）；量能粗篩門檻提升至 2,000 張；汪洋大魚依強勢評分排序。 |
| 2026-05-01 | V7.5 | API 三劍客降載：① Yahoo MA5 前置預篩（攔截 65 支冗餘請求）② Yahoo 取代 FinMind 股價（市場掃描+魚池各省 1 call/股）③ TaiwanStockInfo 7 日獨立快取。實測 API 消耗：430 → 171 次（-60%）。Token 安全修復（env var）。 |
| 2026-04-28 | V7.4 | 新增本地快取機制、API 精確計數器、粗篩量能門檻提升至 1,500 張 |
| 2026-04-28 | — | 資料夾重組（daily json / history / auto radar yml）、建立每日 SOP |
| 2026-04-26 | V7.3 | 新增 FinMind 股價前處理標準化函數、雙重火力補抓機制 |

---

*此檔案由 Claude 與 Jeff 共同維護，請在每次重大協作後更新。*
