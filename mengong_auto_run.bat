@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "C:\AIworkplace\AI Magic\Team stock"
python mengong_auto.py >> mengong_auto.log 2>&1
