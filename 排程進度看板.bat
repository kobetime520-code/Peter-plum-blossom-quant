@echo off
rem 雙擊開啟排程進度看板（前景 Watch 模式，Ctrl+C 或關窗離開）
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0schedule_progress.ps1" -Watch
pause
