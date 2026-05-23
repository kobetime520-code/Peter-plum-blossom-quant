@echo off
chcp 65001 >nul
echo ================================================
echo  孟恭的道路指引 — 自動排程設定
echo  每週三 23:00 / 每週六 17:00 (台灣時間)
echo ================================================
echo.

:: 取得腳本所在目錄
set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%mengong_auto.py

:: 確認 python 可執行
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 python，請確認 Python 已安裝並加入 PATH
    pause
    exit /b 1
)

echo [1/2] 建立「每週三 23:00」排程...
schtasks /create ^
  /tn "MengongAuto_Wed" ^
  /tr "python \"%PYTHON_SCRIPT%\"" ^
  /sc WEEKLY ^
  /d WED ^
  /st 23:00 ^
  /f ^
  /rl HIGHEST
if %errorlevel% equ 0 (
    echo       OK：MengongAuto_Wed 建立成功
) else (
    echo       [警告] 建立失敗，請以系統管理員身份執行此批次檔
)

echo.
echo [2/2] 建立「每週六 17:00」排程...
schtasks /create ^
  /tn "MengongAuto_Sat" ^
  /tr "python \"%PYTHON_SCRIPT%\"" ^
  /sc WEEKLY ^
  /d SAT ^
  /st 17:00 ^
  /f ^
  /rl HIGHEST
if %errorlevel% equ 0 (
    echo       OK：MengongAuto_Sat 建立成功
) else (
    echo       [警告] 建立失敗，請以系統管理員身份執行此批次檔
)

echo.
echo ================================================
echo  排程設定完成！
echo  可至「工作排程器」確認：
echo    開始 → 搜尋「工作排程器」→ 工作排程器程式庫
echo    找到 MengongAuto_Wed / MengongAuto_Sat
echo ================================================
echo.
pause
