# 🌸 彼夫有責戰情室 — 梅花選股量化系統

> 負責人：JW ｜ AI 特助：Jemini ｜ 最後更新：2026-08-01 ｜ 版本：**V9.2 / V9.2 UI**

台股自動選股與監控系統，以量化模型搭配三大法人籌碼，每日自動掃描股票池、輸出操作訊號，協助 JW 做出進出場決策。架構為**方案 B 本地主算**：重度運算在本機（工作排程器）執行，GitHub 僅作靜態戰報展示。

---

## 📖 規格文件在哪裡

本檔僅作導引。**所有系統規格以 [`CLAUDE.md`](CLAUDE.md) 為唯一事實來源**，此處不再複製，避免兩份文件各自漂移。

| 想查什麼 | 去哪裡 |
|---|---|
| 魚池設定與晉升條件 | [`CLAUDE.md`](CLAUDE.md) 「🐠 魚池設定」 |
| 篩選流程、核心指標、強勢評分、籌碼分級 | [`CLAUDE.md`](CLAUDE.md) 「⚙️ 技術架構」 |
| 四條自動排程與手動備援 | [`CLAUDE.md`](CLAUDE.md) 「🤖 自動排程」 |
| 前端雙主題與分頁 | [`CLAUDE.md`](CLAUDE.md) 「🎨 前端主題」 |
| 完整版本更新日誌 | [`CLAUDE.md`](CLAUDE.md) 「📝 版本更新日誌」 |
| 每日人工作業流程 | [`CLAUDE.md`](CLAUDE.md) 「📅 每日作業 SOP」 |
| 成員角色設定（SKILL 正本） | [`docs/05_Team_stock/`](docs/05_Team_stock/) ／ 索引見 [`docs/00_INDEX.md`](docs/00_INDEX.md) |

---

## ⚡ 檔案快速導覽（已集中根目錄）

| 檔案 / 資料夾 | 說明 |
|--------------|------|
| `CLAUDE.md` | 戰情室核心記憶檔（規格唯一事實來源） |
| `radar.py` | 核心雷達掃描程式（正式版，V9.2） |
| `moly.py` / `git_sync.py` | 本地主算入口 / 精準推送（5 個戰報檔白名單） |
| `index.html` / `grace.html` / `mengong.html` | 前端展示頁面（主頁 / Grace 題材 / 孟恭道路指引） |
| `plum_blossom_data.json` | 每日選股戰報 |
| `ocean_history.json` | 記憶海（真·僅追加，出現 ≥ 3 次晉升猛虎池） |
| `log_report.json` / `backtest_report.json` / `grace_theme_data.json` | 維運日誌 / 週回測 / Grace 題材 |
| `backtest_run.py` / `grace_run.py` / `mengong_auto.py` | 排程執行器（回測 / 題材 / 孟恭） |
| `schedule_progress.ps1` / `排程進度看板.bat` | 四排程狀態看板（`-Watch` 即時刷新） |
| `*_cache.json` | 本地快取（`finmind_cache.json` 等，不推送） |
| `.github/workflows/manual_radar_update.yml` | GitHub Actions 手動備援（僅 `workflow_dispatch`，無 cron） |

> `C:\Moly\`（倉庫外）為排程進入點：`moly_start.ps1`（含交易日判斷）、`backtest_start.ps1`、`grace_start.ps1`、`holidays.txt`、`norton_root.pem`。

---

## 🚀 手動執行

```bash
pip install -r requirements.txt

python radar.py            # 雷達掃描（尾端自動 git 推送戰報）
python grace_run.py        # Grace 題材更新
python backtest_run.py     # 週回測
```

> FinMind API token 以環境變數傳入，不寫入程式碼。排程正常運作時無須手動執行；手動跑等同直接發布戰報。

---

*此專案由 Claude（Jemini）與 JW 共同維護。*
