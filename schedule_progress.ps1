# ============================================================
# 彼夫有責戰情室 — 排程進度看板 (schedule_progress.ps1)
# 用途：查看四項本機排程的今日執行進度與戰報檔新鮮度
# 用法：
#   .\schedule_progress.ps1            # 顯示一次即結束
#   .\schedule_progress.ps1 -Watch     # 前景即時刷新（預設 5 秒），Ctrl+C 離開
#   .\schedule_progress.ps1 -Watch -IntervalSec 3 -LogLines 20
# 注意：本腳本為前景執行，不註冊任何背景作業或排程
# ============================================================
param(
    [switch]$Watch,
    [int]$IntervalSec = 5,
    [int]$LogLines = 12
)

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

$TaskDefs = @(
    @{ Name = 'Moly-GraceDaily';     Label = 'Grace 題材更新 '; Sched = '每日 06:00     ' },
    @{ Name = 'Moly-Daily';          Label = 'Moly 雷達掃描  '; Sched = '週一~五 20:39  ' },
    @{ Name = 'MengongAuto_Daily';   Label = '孟恭道路指引   '; Sched = '每日 21:00     ' },
    @{ Name = 'Moly-BacktestWeekly'; Label = '週回測          '; Sched = '週六 06:00     ' }
)

$FileDefs = @(
    @{ Path = 'plum_blossom_data.json'; Label = '選股戰報   ' },
    @{ Path = 'log_report.json';        Label = '維運日誌   ' },
    @{ Path = 'grace_theme_data.json';  Label = 'Grace 題材 ' },
    @{ Path = 'backtest_report.json';   Label = '週回測報告 ' },
    @{ Path = 'mengong_summary.json';   Label = '孟恭彙整   ' }
)

function Get-TaskRow($def) {
    $t = Get-ScheduledTask -TaskName $def.Name -ErrorAction SilentlyContinue
    if (-not $t) {
        return @{ Text = '[缺] 排程未註冊'; Color = 'Red' }
    }
    $i = $t | Get-ScheduledTaskInfo
    $today = (Get-Date).Date

    if ($t.State -eq 'Running') {
        return @{ Text = ('[執行中] 自 {0:HH:mm:ss} 起' -f $i.LastRunTime); Color = 'Cyan' }
    }
    if ($i.LastTaskResult -eq 267011) {
        # 0x00041303：工作尚未執行過
        $next = if ($i.NextRunTime) { '下次 {0:MM/dd HH:mm}' -f $i.NextRunTime } else { '' }
        return @{ Text = "[尚未執行過] $next"; Color = 'DarkGray' }
    }
    if ($i.LastRunTime.Date -eq $today) {
        if ($i.LastTaskResult -eq 0) {
            return @{ Text = ('[今日完成] {0:HH:mm:ss} (code 0)' -f $i.LastRunTime); Color = 'Green' }
        }
        return @{ Text = ('[今日失敗] {0:HH:mm:ss} (code {1})' -f $i.LastRunTime, $i.LastTaskResult); Color = 'Red' }
    }
    if ($i.NextRunTime -and $i.NextRunTime.Date -eq $today) {
        return @{ Text = ('[待執行] 今日 {0:HH:mm}' -f $i.NextRunTime); Color = 'Yellow' }
    }
    $last = if ($i.LastRunTime.Year -gt 2000) { '上次 {0:MM/dd HH:mm}' -f $i.LastRunTime } else { '從未執行' }
    $next = if ($i.NextRunTime) { '下次 {0:MM/dd HH:mm}' -f $i.NextRunTime } else { '' }
    return @{ Text = "[今日無排程] $last $next"; Color = 'DarkGray' }
}

function Show-Dashboard {
    $now = Get-Date
    Write-Host ('═' * 72) -ForegroundColor DarkCyan
    Write-Host ("  彼夫有責戰情室 — 排程進度看板    {0:yyyy/MM/dd (ddd) HH:mm:ss}" -f $now) -ForegroundColor White
    Write-Host ('═' * 72) -ForegroundColor DarkCyan

    Write-Host ''
    Write-Host '── 排程任務狀態 ──────────────────────────────────────' -ForegroundColor DarkCyan
    foreach ($def in $TaskDefs) {
        $row = Get-TaskRow $def
        Write-Host ("  {0}| {1}| " -f $def.Label, $def.Sched) -NoNewline
        Write-Host $row.Text -ForegroundColor $row.Color
    }

    Write-Host ''
    Write-Host '── 戰報檔新鮮度 ──────────────────────────────────────' -ForegroundColor DarkCyan
    foreach ($def in $FileDefs) {
        $p = Join-Path $Root $def.Path
        if (Test-Path $p) {
            $f = Get-Item $p
            $age = (Get-Date) - $f.LastWriteTime
            $ageText = if ($age.TotalHours -lt 1) { '{0:N0} 分鐘前' -f $age.TotalMinutes }
                       elseif ($age.TotalDays -lt 1) { '{0:N1} 小時前' -f $age.TotalHours }
                       else { '{0:N1} 天前' -f $age.TotalDays }
            $color = if ($f.LastWriteTime.Date -eq (Get-Date).Date) { 'Green' } elseif ($age.TotalDays -lt 8) { 'Yellow' } else { 'Red' }
            Write-Host ("  {0}| {1:MM/dd HH:mm:ss} | " -f $def.Label, $f.LastWriteTime) -NoNewline
            Write-Host $ageText -ForegroundColor $color
        } else {
            Write-Host ("  {0}| 檔案不存在" -f $def.Label) -ForegroundColor Red
        }
    }

    $logReport = Join-Path $Root 'log_report.json'
    if (Test-Path $logReport) {
        try {
            $r = Get-Content $logReport -Raw -Encoding UTF8 | ConvertFrom-Json
            Write-Host ''
            Write-Host '── 最近一次雷達掃描結果 (log_report.json) ────────────' -ForegroundColor DarkCyan
            $statusColor = if ($r.status -eq 'Success') { 'Green' } else { 'Red' }
            Write-Host ("  更新時間 {0} | 處理 {1} 支 | API {2} 次 | 快取 {3} 次" -f $r.last_update, $r.stocks_processed, $r.api_usage_count, $r.cache_hits)
            Write-Host ("  掃描狀態 {0} | 推送狀態 {1}" -f $r.status, $r.push_status) -ForegroundColor $statusColor
        } catch {
            Write-Host '  log_report.json 解析失敗' -ForegroundColor Red
        }
    }

    # 日誌來源切換：Moly-Daily 執行中讀 radar_run.log（moly.py 將 radar.py stdout 導向此檔，
    # 逐批掃描進度所在；PYTHONUNBUFFERED=1 使其即時落地）；平時讀 moly.log（logger 摘要）
    # 註：moly_ps.log 僅含 moly.py logger 與 git_sync 輸出，無 radar 逐批進度，故不作為即時來源
    $molyRunning = (Get-ScheduledTask -TaskName 'Moly-Daily' -ErrorAction SilentlyContinue).State -eq 'Running'
    $radarLog = Join-Path $Root 'radar_run.log'
    if ($molyRunning -and (Test-Path $radarLog)) {
        $molyLog = $radarLog
        $logTitle = '── 🔴 即時掃描進度 radar_run.log（最後 {0} 行）─────────' -f $LogLines
    } else {
        $molyLog = Join-Path $Root 'moly.log'
        $logTitle = '── Moly 執行日誌 moly.log（最後 {0} 行）───────────────' -f $LogLines
    }
    if (Test-Path $molyLog) {
        Write-Host ''
        Write-Host $logTitle -ForegroundColor DarkCyan
        # 兩者皆為 Python 以 UTF-8 寫出
        Get-Content $molyLog -Tail $LogLines -Encoding UTF8 | ForEach-Object {
            $color = if ($_ -match '失敗|錯誤|Error|Fail') { 'Red' } elseif ($_ -match '完成|成功|OK') { 'Green' } else { 'Gray' }
            Write-Host "  $_" -ForegroundColor $color
        }
    }

    Write-Host ''
    if ($Watch) {
        Write-Host ("  [Watch 模式] 每 {0} 秒刷新，Ctrl+C 離開" -f $IntervalSec) -ForegroundColor DarkGray
    }
    Write-Host ('═' * 72) -ForegroundColor DarkCyan
}

if ($Watch) {
    while ($true) {
        Clear-Host
        Show-Dashboard
        Start-Sleep -Seconds $IntervalSec
    }
} else {
    Show-Dashboard
}
