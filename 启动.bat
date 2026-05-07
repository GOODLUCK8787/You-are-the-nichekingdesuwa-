@echo off
title Niche King - Sakiko Togawa

echo.
echo   Niche King
echo   Judged by Sakiko Togawa (Ave Mujica)
echo.

cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [ERROR] Python not found. Please install Python 3.12+
    echo   https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Install dependencies if needed
python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo   [INSTALL] Installing dependencies...
    pip install -e . -q
    echo.
)

:: Launch
echo   [START] Sakiko is here...
echo.
start "" http://localhost:8501
python -m streamlit run src/yinyue/ui/app.py --server.port 8501

pause
