@echo off
title BMS Automation Bot Launcher
color 0F

:: Ensure the script runs in the correct folder even if run as admin
cd /d "%~dp0"

echo ==========================================
echo   Starting BMS Automation Bot...
echo ==========================================

:: Activate the virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [!] Warning: .venv not found. Attempting to run on global Python...
)

:: Run the main launcher
python launcher.py

:: Keep the window open if it crashes
pause