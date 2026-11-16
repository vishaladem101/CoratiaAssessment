#!/usr/bin/env bash
# ==============================================================================
# ROV Telemetry Ground Station - macOS Launcher (Double-Click in Finder)
# ==============================================================================
set -e

cd "$(dirname "$0")/.."

echo "============================================================"
echo " Starting ROV Dam Inspection Ground Station (macOS)         "
echo "============================================================"

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 was not found."
    echo "Please install Python 3 or run 'brew install python' using Homebrew."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "[SETUP] Creating isolated virtual environment 'venv'..."
    python3 -m venv venv
    echo "[SETUP] Installing required libraries (PySide6, pyqtgraph, numpy)..."
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r scripts/requirements.txt
fi

echo "[LAUNCH] Launching ROV Telemetry Dashboard..."
./venv/bin/python3 main.py

