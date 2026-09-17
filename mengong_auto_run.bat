@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "C:\AIworkplace\AI Magic\Team stock"

rem === Log rotation (audit E1 / F-12) ======================================
rem NOTE: keep this file pure ASCII. cmd.exe parses .bat with the system ANSI
rem codepage (CP950 here), so UTF-8 Chinese comments corrupt line parsing and
rem abort the script before python ever starts. chcp 65001 above only affects
rem console output, NOT how cmd reads this file. (Root cause of 08/02-08/03
rem MengongAuto_Daily failures, exit code 255, zero log output.)
rem
rem mengong_auto.log is produced by the >> redirect below and is held by cmd,
rem so the Python side cannot rotate it. Check the size before launching
rem python: over 2 MB, rename to .old (keep one generation only).
rem The size is read in a subroutine (call :rotate_log) to avoid reading a
rem variable set inside the same if block, which would need delayed expansion.
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
    echo [rotate] %LOGFILE% exceeded %LOGMAX% bytes, archived as %LOGFILE%.old
)
goto :eof
