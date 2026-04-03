@echo off
title CodeVision (Gemini) - Starting...
echo.
echo  ==========================================
echo   CodeVision - AI Code Analysis (Gemini)
echo  ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found.
    echo  Install from https://python.org and tick "Add to PATH"
    pause
    exit /b
)

REM Go to backend folder
cd /d "%~dp0backend"

REM Create venv if not exists
if not exist "venv" (
    echo  Setting up virtual environment...
    python -m venv venv
)

REM Activate
call venv\Scripts\activate.bat

REM Install deps
echo  Installing dependencies...
pip install -r requirements.txt -q

REM Check API key
if not exist ".env" (
    echo.
    echo  SETUP REQUIRED:
    echo  1. Get your FREE Gemini API key from https://aistudio.google.com/apikey
    echo  2. Open the file:  backend\.env
    echo  3. Replace  YOUR_KEY_HERE  with your actual key
    echo  4. Save and run this script again
    echo.
    echo GEMINI_API_KEY=YOUR_KEY_HERE> .env
    notepad .env
    pause
    exit /b
)

REM Check if key is still placeholder
findstr /C:"YOUR_KEY_HERE" .env >nul 2>&1
if not errorlevel 1 (
    echo.
    echo  API key not set. Edit backend\.env and replace YOUR_KEY_HERE
    notepad .env
    pause
    exit /b
)

REM Start server and open browser
echo.
echo  Starting CodeVision at http://localhost:8000
echo  Press Ctrl+C to stop
echo.
start "" http://localhost:8000
python -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
