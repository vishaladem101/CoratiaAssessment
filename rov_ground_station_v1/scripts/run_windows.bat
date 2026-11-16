@echo off
:: ==============================================================================
:: ROV Telemetry Ground Station - Windows Launcher (Double-Click to Run)
:: ==============================================================================
title ROV Ground Station - Nagarjuna Sagar Dam Inspection

cd /d "%~dp0\.."

echo ============================================================
echo  Starting ROV Ground Station (Windows)
echo ============================================================

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in your system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

if not exist "venv" (
    echo [SETUP] Creating isolated virtual environment 'venv'...
    python -m venv venv
    echo [SETUP] Installing required libraries (PySide6, pyqtgraph, numpy)...
    venv\Scripts\pip install --upgrade pip
    venv\Scripts\pip install -r scripts\requirements.txt
)

echo [LAUNCH] Launching ROV Telemetry Dashboard...
venv\Scripts\python main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Application encountered an error on exit.
    pause
)

