@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 啟動 Uma Musume 自動育成程式...
echo 按 ESC 可隨時停止
echo.
python src/auto_main.py
pause
