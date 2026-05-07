@echo off
chcp 65001 >nul
title 你才是真正的小众king - 丰川祥子

echo.
echo   🎭 你才是真正的小众king
echo   豊川祥子（Ave Mujica）による審判
echo.

cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [错误] 未找到 Python，请先安装 Python 3.12+
    echo   下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Install dependencies if needed
python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo   [安装] 正在安装依赖，稍等...
    pip install -e . -q
    echo.
)

:: Launch
echo   [启动] 祥子来了...
echo.
start "" http://localhost:8501
python -m streamlit run src/yinyue/ui/app.py --server.port 8501

pause
