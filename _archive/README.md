# _archive／已停用檔案

2026-08-01 檔案盤點稽核（E2／E3，對應發現 F-13）將已無呼叫者、或已被取代的檔案
集中於此，**不做實體刪除**，保留追溯能力。

> ⚠️ 此資料夾內的檔案**一律不要直接執行**。其中 `moly_start.bat` 特別容易誤用 ——
> 它沒有交易日判斷，直接執行會在假日產出無效戰報。

## 內容

| 檔案 | 停用日 | 停用原因 | 現行替代 |
|---|---|---|---|
| `moly_start.bat` | 2026-07-04 | 新機移轉後排程改用倉庫外的啟動腳本；本檔無交易日判斷，誤用會在假日產出無效戰報 | `C:\Moly\moly_start.ps1`（含交易日判斷） |
| `mengong_summary.py` | 2026-06-03 | 功能已併入 `mengong_auto.py`（改為本機規則式彙整、無需 API），無任何呼叫者 | `mengong_auto.py`（每日 21:00 排程） |
| `setup_mengong_schedule.bat` | 2026-06-03 | 一次性排程註冊工具，`MengongAuto_Daily` 早已註冊完成 | Windows 工作排程器現行設定 |
| `MengongAuto_Daily.xml` | 2026-06-03 | 上述註冊工具匯出的工作定義備份 | 同上 |
| `moly_legacy_20260704.log` | 2026-07-04 | 編碼修復事件的歷史保留（CP950 損毀） | `moly.log`（2026-08-01 起自動輪替） |
| `moly_ps_legacy_20260709.log` | 2026-07-09 | 編碼修復事件的歷史保留（UTF-16 污染） | `moly_ps.log` |
| `institutional_investors_test.csv` | 2026-05-09 | `finmind_gateway testing/` 唯一殘留檔，父層兩級皆為空殼目錄，已一併移除 | 無（測試資料） |
| `yongguang_transcript.txt` | 2026-06-14 | 逐字稿素材暫存，非系統檔案 | 無 |

## 同時清除的殘留（無保留價值，未歸檔）

- `docs/05_Team_stock/晨報/desktop.ini` —— 空資料夾殘留的 Windows 設定檔。
  `.gitignore` 早已列出「晨報/」，但該檔在規則之前就被追蹤故排除無效，
  以 `git rm --cached` 解除追蹤後連同空目錄移除。
- `__pycache__/` —— Python 建置產物。
- `.claude/worktrees/` —— 兩個空的 worktree 目錄（`git worktree list` 確認未註冊、內含 0 個檔案）。
