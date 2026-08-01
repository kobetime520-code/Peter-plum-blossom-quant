# 📚 docs 知識庫總索引

> 最後更新：2026-08-01 ｜ 維護：JW & Claude
>
> 本檔為**位置索引**，不載明規格與版本號。系統規格見 [`CLAUDE.md`](../CLAUDE.md)（唯一事實來源）；成員版本以各 SKILL 檔尾自述為準。

`docs/` 現僅存放 **Team Stock 成員 SKILL 正本**（`05_Team_stock/`，git 版控）。
其餘團隊的 SKILL 正本位於各 Team 資料夾（repo 外），原 `01~04` 過時鏡像副本已於 2026-07-06 移除（`git rm`，歷史保留，可隨時還原）。

---

## 🗂️ 各團隊 SKILL 正本位置一覽

| 團隊 | 正本位置（本機） | 成員 |
|------|----------------|------|
| 🏢 AI 總管理處 | `C:\AIworkplace\AI Magic\AI總管理處\` | Sidey、Ken、Joseph ＋ 清冊/架構圖/公告日期版系列（最新 20260706） |
| 🤖 Team AI | `C:\AIworkplace\AI Magic\Team AI\` | Ted（V2.0）＋ IT_memory.md |
| 🏠 Team Life | `C:\AIworkplace\AI Magic\Team Life\` | ChingWen ＋ 教育/財管/家庭/旅遊四顧問 ＋ Life_memory.md |
| 🏭 Team PID | `C:\AIworkplace\AI Magic\Team PID\` | Jeff（協理）、Oscar、Ann、Sian、Luci、Edda ＋ PID_memory.md |
| 📈 Team Stock | `docs/05_Team_stock/`（本 repo） | 見下表 |
| ✨ Magic Lab | `C:\AIworkplace\AI Agent\` | Terry、Miles、Wayne、Wesley（Claude Code skill 形式） |

> 全員已註冊 Claude Code agent：`C:\AIworkplace\.claude\agents\`（**29 位**，2026-08-01 實地清點）。
> 總清冊：`AI總管理處\團隊人員清冊與Skill核對表_20260706.md`｜Agent 速查：`AI總管理處\AI員工總清單_25Agent_20260706.md`（檔名停在 25 位，內容待補）

---

## 📈 05_Team_stock（Team Stock 成員 SKILL 正本）

> ⚠️ 版本號不在此表維護。各成員版本以 **SKILL 檔尾自述**為準，避免索引與正本漂移（2026-08-01 稽核 C1／發現 F-04）。
>
> ℹ️ Zoey 有兩份檔案且**刻意不合併**（2026-08-01 稽核 D2／發現 F-10）：`Zoey_SKILL.md` 是「誰在做、以什麼立場做」的角色人格，`Zoey_war-room-designer_SKILL.md` 是「用什麼流程做」的視覺設計方法論，且後者已獨立安裝為全域 skill（`C:\AIworkplace\.claude\skills\war-room-designer\`），合併會破壞該安裝。改動工具包時須同步安裝副本。

| 檔案 | 說明 |
|------|------|
| [`Peter_SKILL.md`](05_Team_stock/Peter_SKILL.md) | Peter — 投資執行長 & 策略長 |
| [`Maple_SKILL.md`](05_Team_stock/Maple_SKILL.md) | Maple — 投資採購及財務長 |
| [`Right_SKILL.md`](05_Team_stock/Right_SKILL.md) | Right — 投資研發長（架構與 API 降載） |
| [`Left_SKILL.md`](05_Team_stock/Left_SKILL.md) | Left — 投資程設助理（Git/Bug/UI） |
| [`Moly_SKILL.md`](05_Team_stock/Moly_SKILL.md) | Moly — 投資排程營運長（本機四排程） |
| [`Zoey_SKILL.md`](05_Team_stock/Zoey_SKILL.md) | Zoey — 投資行銷創意長（Dashboard 2.0）｜**角色人格正本**，觸發：「請用 Zoey 身份」 |
| [`Zoey_war-room-designer_SKILL.md`](05_Team_stock/Zoey_war-room-designer_SKILL.md) | Zoey — 戰情室視覺設計｜**方法論工具包**（已獨立安裝為全域 skill `war-room-designer`），觸發：「Dashboard 設計」「加個圖表」 |
| [`Tim_SKILL.md`](05_Team_stock/Tim_SKILL.md) | Tim — 基本面研究員（楓大永動/彼神黃金） |
| [`Grace_SKILL.md`](05_Team_stock/Grace_SKILL.md) | Grace — 題材面研究員 & 高階投資顧問 |
| [`Joe_SKILL.md`](05_Team_stock/Joe_SKILL.md) | Joe — 技術面研究員（+quant-research 回測） |
| [`Eric_SKILL.md`](05_Team_stock/Eric_SKILL.md) | Eric — 籌碼分析研究員（A1 閘門、姊夫池融資閘門） |

### 📰 05_Team_stock/晨報

已於 2026-08-01（稽核 E3）移除。晨報版角色設定早已併入正式 SKILL，該目錄僅剩一支被誤追蹤的 `desktop.ini`。

---

## 📌 說明

- 本機路徑：`C:\AIworkplace\AI Magic\`
- GitHub Repo：`kobetime520-code/Peter-plum-blossom-quant`
- 同步方式：Moly 每日排程 git 推送（戰報）＋ 手動 `git push`（文件）
- 還原已刪副本：`git log -- "docs/01_AI總管理處"` 找到 commit 後 `git checkout <commit>^ -- <路徑>`

---

*由 Claude 更新 ｜ 2026-08-01 稽核 C1（原版由 Jemini 生成，2026-05-12；2026-07-06 改版）*
