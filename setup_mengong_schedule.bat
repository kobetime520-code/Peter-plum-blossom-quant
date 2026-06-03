@echo off
chcp 65001 >nul

:: ===== 自我提權：若非系統管理員，自動跳出 UAC 重新啟動 =====
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 需要系統管理員權限，正在跳出授權視窗...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ================================================
echo  孟恭的道路指引 — 自動排程設定
echo  每天 21:00（晚上 9 點，台灣時間）｜ 無需任何 API
echo  [已取得系統管理員權限]
echo ================================================
echo.

:: 取得腳本所在目錄
set SCRIPT_DIR=%~dp0
set RUN_BAT=%SCRIPT_DIR%mengong_auto_run.bat

:: 確認 python 可執行
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 python，請確認 Python 已安裝並加入 PATH
    pause
    exit /b 1
)

echo [1/3] 移除舊排程（週三 / 週六，若存在）...
schtasks /delete /tn "MengongAuto_Wed" /f >nul 2>&1
schtasks /delete /tn "MengongAuto_Sat" /f >nul 2>&1
echo       OK：舊排程已清除（若原本不存在則略過）

echo.
echo [2/3] 建立「每天 21:00」排程...
schtasks /create ^
  /tn "MengongAuto_Daily" ^
  /tr "cmd.exe /c \"%RUN_BAT%\"" ^
  /sc DAILY ^
  /st 21:00 ^
  /f ^
  /rl HIGHEST
if %errorlevel% equ 0 (
    echo       OK：MengongAuto_Daily 建立成功
) else (
    echo       [警告] 建立失敗，請以系統管理員身份執行此批次檔
)

echo.
echo [3/3] 確認排程狀態...
schtasks /query /tn "MengongAuto_Daily" /fo LIST | findstr /C:"TaskName" /C:"Next Run Time" /C:"Status"

echo.
echo ================================================
echo  排程設定完成！每天台灣時間 21:00 自動更新孟恭最新資訊
echo  可至「工作排程器」確認：MengongAuto_Daily
echo ================================================
echo.
pause
