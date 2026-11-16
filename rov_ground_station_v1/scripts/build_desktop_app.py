#!/usr/bin/env python3
"""
Cross-Platform Build Script for ROV Ground Station Desktop Application.
Works on:
  - Windows -> generates dist/ROVGroundStation/ROVGroundStation.exe
  - Linux (Ubuntu) -> generates dist/ROVGroundStation/ROVGroundStation
  - macOS -> generates dist/ROVGroundStation/ROVGroundStation.app

Usage:
  python build_desktop_app.py
"""

import os
import sys
import subprocess
import platform

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

def main():
    os.chdir(PROJECT_ROOT)
    system = platform.system()
    print("=" * 60)
    print(f" Building ROV Ground Station for {system} ({platform.machine()}) ")
    print("=" * 60)

    # 1. Check PyInstaller
    try:
        import PyInstaller
        print(f"[OK] Found PyInstaller version {PyInstaller.__version__}")
    except ImportError:
        print("[SETUP] PyInstaller not found. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Run PyInstaller pointing to spec file in scripts/
    spec_path = os.path.join(SCRIPT_DIR, "ROVGroundStation.spec")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", spec_path]
    print(f"[BUILD] Executing: {' '.join(cmd)}")
    subprocess.check_call(cmd)

    print("\n" + "=" * 60)
    if system == "Windows":
        print(" [SUCCESS] Build Complete!")
        print(" Executable: dist\\ROVGroundStation\\ROVGroundStation.exe")
    elif system == "Darwin":
        print(" [SUCCESS] Build Complete!")
        print(" App Bundle: dist/ROVGroundStation/ROVGroundStation.app")
    else:
        print(" [SUCCESS] Build Complete!")
        print(" Executable: dist/ROVGroundStation/ROVGroundStation")
    print("=" * 60)

if __name__ == "__main__":
    main()

