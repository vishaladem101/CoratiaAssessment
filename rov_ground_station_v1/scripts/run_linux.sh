#!/usr/bin/env bash
# ==============================================================================
# ROV Telemetry Ground Station - Linux (Ubuntu) Launcher
# ==============================================================================
set -e

cd "$(dirname "$0")/.."

echo "============================================================"
echo " Starting ROV Dam Inspection Ground Station (Linux/Ubuntu) "
echo "============================================================"

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install Python 3 (sudo apt install python3 python3-venv)."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment 'venv'..."
    python3 -m venv venv
    echo "Installing required dependencies..."
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r scripts/requirements.txt
fi

# Run the app
./venv/bin/python3 main.py

