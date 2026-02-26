@echo off
title WIS - Startup
echo Starting WIS (Webhook Image Sender)...

:: Check if Python is installed
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b
)

:: Create virtual environment if it doesn't exist
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

:: Activate environment and update dependencies
echo Checking dependencies...
call .venv\Scripts\activate
pip install -r requirements.txt --quiet

:: Launch the application
:: We use pythonw.exe to run it without a persistent black console window
echo Launching application...
start "" .venv\Scripts\pythonw.exe main.py
exit