@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "C:\AIworkplace\AI Magic\Team stock"

rem === 日誌輪替（稽核 E1／F-12）==============================================
rem mengong_auto.log 由本檔的 >> 重導產生，檔案由 cmd 持有，Python 端無法輪替，
rem 故在啟動 python 前先檢查大小：超過 2 MB 就改名歸檔，最多保留一份 .old。
rem 以子程序（call :rotate_log）取得檔案大小，避免在 if 區塊內取用同區塊剛設定
rem 的變數（該情境需延遲展開，是常見的 batch 陷阱）。
set "LOGFILE=mengong_auto.log"
set "LOGMAX=2000000"
if exist "%LOGFILE%" call :rotate_log

"C:\Users\User\AppData\Local\Programs\Python\Python313\python.exe" mengong_auto.py >> "%LOGFILE%" 2>&1
exit /b %ERRORLEVEL%

:rotate_log
for %%A in ("%LOGFILE%") do set "LOGSIZE=%%~zA"
if %LOGSIZE% GTR %LOGMAX% (
    if exist "%LOGFILE%.old" del "%LOGFILE%.old"
    move /y "%LOGFILE%" "%LOGFILE%.old" >nul
    echo [rotate] %LOGFILE% 超過 %LOGMAX% bytes，已歸檔為 %LOGFILE%.old
)
goto :eof
