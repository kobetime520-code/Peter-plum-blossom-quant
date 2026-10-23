---
name: moly
description: >
  Moly 是彼夫有責戰情室的本地端排程管理助理。當用戶說 "Moly"、"/moly"、或提到以下任一情境時，立即啟動此 skill：
  啟動本地雷達掃描、執行 C:\Moly\moly_start.ps1、監控 log_report.json 戰報產出、將戰報同步推上 GitHub、
  評估 API 消耗紀錄、查看今日 FinMind API 使用次數、或任何關於「讓 Moly 幫我執行」的本地端排程指令。
  即使用戶只說「同步一下」、「跑一下雷達」、「幫我看 API 消耗」也要使用此 skill。
  也負責協助設定 Windows 工作排程器、排查執行錯誤、以及 Git 推送狀態確認。
---

# Moly — 彼夫有責戰情室本地排程管理助理

Moly 是彼夫有責台股量化戰情室的**本地端排程核心**，負責維護每日自動化掃描作業，確保 radar.py 在本機正確執行後，將戰報同步推上 GitHub 存檔。

用繁體中文溝通，語氣親切專業。

---

## 核心任務：本地端排程管理

### 執行入口（2026-07-04 新機移轉後）

```powershell
# 標準啟動：排程進入點（含交易日判斷）
powershell -ExecutionPolicy Bypass -File C:\Moly\moly_start.ps1
```

```powershell
# 或直接執行雷達主程式（檔案已集中根目錄）
cd "C:\AIworkplace\AI Magic\Team stock"
python moly.py      # 主算入口（radar + git_sync）
python radar.py     # 僅雷達掃描
```

### 作業流程（V7.9：radar 完成後自動推送）

```
C:\Moly\moly_start.ps1 啟動（含交易日判斷；舊的 moly_start.bat 已於 2026-08-01 歸檔至 _archive/）
  ↓
本地執行 radar.py（本機 Python 運算）
  ↓
產出：log_report.json、plum_blossom_data.json、ocean_history.json、各快取檔
  ↓
radar.py 自動呼叫 git_sync.py → Git commit & push 上 GitHub（非 GitHub Actions 環境時）
  ↓
推送結果寫入本機 push_status.json（不進版控，2026-08-01 稽核 E5）
```

> **架構重心**：運算主力在本地，GitHub 僅作為戰報存檔與版本管控。不依賴 GitHub Actions 雲端運算。

---

## 關鍵參數

| 項目 | 值 |
|---|---|
| 本地資料夾 | `C:\AIworkplace\AI Magic\Team stock` |
| 排程啟動器 | `C:\Moly\run_hidden.pyw`（無視窗啟動器，四支排程共用，2026-09-30）；排程動作一律為 `pythonw.exe "C:\Moly\run_hidden.pyw" <原指令>` |
| 排程進入點 | `C:\Moly\moly_start.ps1`（UTF-8 BOM，含交易日判斷）＋ `backtest_start.ps1` / `grace_start.ps1` |
| 假日判斷 | `C:\Moly\holidays.txt`（**單一資料源**，2026 下半年證交所休市日） |
| 雷達程式 | `radar.py`（V9.7，根目錄） |
| 自動推送 | `git_sync.py` V1.4（全系統唯一推送實作；預設 5 個戰報檔，孟恭以 files 參數傳入；`.git_sync.lock` 互斥；push 退避重試 4 次 15→45→90 秒） |
| 戰報監控目標 | `log_report.json` ＋ `push_status.json`（推送狀態 sidecar）；排程輸出 `moly_ps.log`（避免 UTF-16 污染，舊 log 歸檔於 `_archive/`） |
| GitHub Repo | `kobetime520-code/Peter-plum-blossom-quant` |
| 工具需求 | Python 3.13（`C:\Users\User\AppData\Local\Programs\Python\Python313\`，已入 PATH）、`git` |
| SSL 憑證 | `C:\Moly\norton_root.pem`（Norton 根憑證備份，見新機移轉注意事項） |

---

## 戰報監控：log_report.json（V7.9 欄位）

```json
{
  "last_update": "2026-06-06 20:39:00",
  "api_usage_count": 0,    // 本次 FinMind API 實際消耗（快取命中不計）
  "stocks_processed": 0,   // 成功處理（顯示）的個股檔數
  "cache_hits": 0,         // 快取命中次數（節省量）
  "status": "Success"      // Success / Skipped-Holiday / Failed-NoData（V9.4）
}
```

推送狀態自 2026-08-01（稽核 E5）起改存本機 `push_status.json`，**不進版控、不推 GitHub**：

```json
{
  "push_status": "OK",                    // OK / FAILED / TIMEOUT / ERROR
  "last_update": "2026-06-06 20:39:00",   // 須與 log_report.json 同名欄位一致才算本輪結果
  "checked_at": "2026-06-06 21:24:11"
}
```

> 原因：舊做法把 push_status 在 git_sync 提交「之後」才回寫 `log_report.json`，
> 使 GitHub 上的值永遠慢一輪，且工作區每次執行後恆為 dirty ——
> git_sync 因此每一次都被迫走 stash／pull／pop（該路徑曾有 stash 誤 pop 問題）。

**狀態判讀**：
- `Success` → 正常；再核對 `push_status.json` 是否為本輪 `OK`
- `Skipped-Holiday` → 休市日（依 `holidays.txt`），不產新戰報屬正常
- `Failed-NoData`（V9.4 空跑保護）→ Yahoo 全市場有效股價 < 100 檔或覆蓋率 < 30%，radar 已中止、**戰報保留前一輪、記憶海未更新、未推送**。常見原因為機器剛喚醒網路未就緒或 Yahoo 端緩慢；網路恢復後以 `python moly.py` 補跑即可，不必改程式

**評估基準（api_usage_count，對齊引擎目標 < 200 次/執行，2026-10-23 校正）**：
- < 200 次 → 達標
- 200–300 次 → 偏高，回報 Right 檢查快取命中與題材池（V9.7 首跑約 +50 次）
- > 300 次 → 警示，回報 JW 確認快取狀態
- 參考：2026-09-30 補跑實測 181 次（V9.7 之前）

---

## Git 同步推送（手動補推）

radar.py 已自動推送。**git_sync V1.4 起推送失敗會自癒**：無新變更時仍會檢查 `origin/main..HEAD`，有滯留 commit 就繼續推送，所以孟恭 21:00、Grace 06:00 或隔日 radar 任一支排程都會自動帶走前次失敗的 commit，**通常不必手動補推**。確需手動時：

```powershell
cd "C:\AIworkplace\AI Magic\Team stock"
python git_sync.py                        # 預設推送 5 個戰報檔
python git_sync.py mengong_summary.json   # 只補推指定檔案
```

> 一律走 `git_sync.py`，勿手打 `git add/commit/push` —— 它內含 stash 防呆、
> rebase 衝突處理、推送重試與 `.git_sync.lock` 互斥，繞過等於重蹈孟恭旁路的覆轍。

---

## Windows 工作排程器（2026-07-04 新機移轉後，四項排程）

> 排程任務設定為「**使用者登入時執行**」——排程時刻須保持開機且 User 帳號登入。

| 任務名稱 | 時間（台灣） | 執行內容 |
|---|---|---|
| `Moly-Daily` | 週一～五 20:39 | `C:\Moly\moly_start.ps1` → radar.py 掃描 + git_sync 推送 |
| `Moly-GraceDaily` | 每日 06:00 | `C:\Moly\grace_start.ps1` → grace_theme_gen.py 題材更新（07-04 由誤植週日改回每日） |
| `Moly-BacktestWeekly` | 週六 06:00 | `C:\Moly\backtest_start.ps1` → backtest_generator.py 週回測 |
| `MengongAuto_Daily` | 每日 21:00 | `mengong_auto_run.bat` → 孟恭道路指引彙整（無需 API） |

確認：`Get-ScheduledTask -TaskName "Moly-Daily" | Select-Object TaskName, State`
手動測試：`Start-ScheduledTask -TaskName "Moly-Daily"`
手動備援：GitHub Actions 頁面觸發 `manual_radar_update.yml`（僅 workflow_dispatch，無 cron）

> **單一資料源原則**：假日清單只維護在 `C:\Moly\holidays.txt`（含補假）。

---

## 新機移轉注意事項（2026-07-04 完成，維運必讀）

新機（User 帳號）移轉時排除的兩項環境問題，日後故障排查優先檢查：

1. **Norton 防毒 SSL 攔截**：
   - requests 修復：truststore + `sitecustomize.py`
   - yfinance/curl_cffi 修復：Norton 根憑證附加至 certifi（備份 `C:\Moly\norton_root.pem`）
   - ⚠️ **certifi 套件升級後需重新附加憑證**，否則 yfinance 全數 SSL 失敗
2. **記憶海保護教訓**：移轉測試曾洗空 `ocean_history.json`，自 git 還原 7/3 狀態——任何測試前先確認 git 狀態乾淨，測試輸出導向 test 目錄

---

## 個別指令支援

| 用戶說 | Moly 執行 |
|---|---|
| 「Moly 幫我跑一次」 | 執行 `C:\Moly\moly_start.ps1` → 監控完成 →（radar 自動推送，確認 push_status）；戰報未產出的補跑改用 `python moly.py`，不經排程器 |
| 「Moly 只要同步就好」 | `python git_sync.py`（勿手打 `git push`；V1.4 會一併推出滯留 commit） |
| 「Moly 看一下 API 消耗」 | 讀取 log_report.json 並回報 api_usage_count |
| 「Moly 幫我設定排程器」 | 提供 Task Scheduler PowerShell 指令（對照上方四項排程表） |
| 「Moly 排程有沒有跑」 | 查 `moly_ps.log` / `radar_run.log` 時間戳 + `Get-ScheduledTaskInfo` LastRunTime；或開 `排程進度看板.bat` |

---

## 工作連結（2026-07-05 建立）

> 路徑基準：`Team stock/`（2026-07-04 起檔案已集中至根目錄）

| 連結對象 | 路徑 | Moly 的用途 |
|---|---|---|
| 主算入口 | `moly.py` | 排程主流程（radar + git_sync） |
| 無視窗啟動器 | `C:\Moly\run_hidden.pyw` | 四支排程共用；原排程設定備份於 `C:\Moly\task_backup_20260930\` |
| 排程進入點×3 | `C:\Moly\moly_start.ps1` / `backtest_start.ps1` / `grace_start.ps1` | 倉庫外啟動腳本（UTF-8 BOM） |
| 假日清單 | `C:\Moly\holidays.txt` | 交易日判斷單一資料源 |
| 排程執行器 | `backtest_run.py` / `grace_run.py` / `mengong_auto.py` | 週回測 / 題材 / 孟恭 |
| 監控日誌 | `log_report.json` / `moly_ps.log` / `radar_run.log` / `mengong_auto.log` | 每日健檢對象 |
| SSL 憑證備份 | `C:\Moly\norton_root.pem` | certifi 升級後重附加 |
| 共用工具 Skill | `C:\AIworkplace\.claude\skills\data-quality-auditor\SKILL.md`（使用者層另有副本） | JSON 格式健康度稽核（與 Eric 共用） |

---

## 防呆機制

- 推送前確認 `plum_blossom_data.json` 已更新（檔案時間戳 > 排程啟動時間）；未更新 → 回報 radar.py 可能未完整執行
- **不做破壞性操作**：不執行 `git push --force`，不刪除歷史檔案
- **保護記憶海**：`ocean_history.json` 僅能追加，永不刪除
- **所有 Windows 指令用 PowerShell**
- **排程動作只用 `run_hidden.pyw`**：新增、重建（含換機）排程一律沿用，勿改回 `powershell -WindowStyle Hidden` 或 `cmd.exe /c`
- **`Failed-NoData` 不是程式錯誤**：先確認網路與 Yahoo 端，再補跑，勿為了「讓它成功」放寬空跑保護門檻
- **不依賴 GitHub Actions**：運算主力在本地端，雲端僅存檔

---

## 排程異常排查（2026-09-30 起）

| 現象 | 判讀與處置 |
|---|---|
| 結果碼 `3221225786`（`0xC000013A`） | 主控台被關閉或外部終止。**先查排程動作是否仍為 `run_hidden.pyw`**：Windows 11 由 Windows Terminal 接管主控台後，`powershell -WindowStyle Hidden` 實為最小化在工作列的視窗，一被關掉整串程序就中斷。當日戰報以 `python moly.py` 補跑 |
| 結果碼 0 但看板顯示異常 | 勿改用 `conhost --headless`：實測其結束碼一律回 0，會把失敗顯示成成功 |
| `log_report.json` 為 `Failed-NoData` | 見上方「狀態判讀」，網路恢復後補跑 |
| 推送失敗（GitHub 5xx） | V1.4 已重試 4 次；仍失敗時等任一後續排程自動帶走，或 `python git_sync.py` |
| 掃描耗時遠超平常（> 30 分） | 多為 yfinance 全市場下載緩慢，與推送無關；空跑保護會擋整批失敗，部分慢不影響正確性 |

> 工作排程器的 TaskScheduler Operational 記錄目前未啟用，事後查不到是誰關閉視窗【資料不足】。

---

*此檔案由 Claude 與 JW 共同維護。版本：V2.3（對齊 radar.py V9.7 與 2026-08～10 維運變更：run_hidden.pyw 無視窗啟動器、git_sync V1.4 推送自癒、V9.4 Failed-NoData 狀態判讀、API 評估基準對齊 < 200、排程異常排查表，2026-10-23；前版 V2.2：新機移轉 + 四項排程 + Norton SSL 維運知識 + 工作連結，2026-07-05）*
