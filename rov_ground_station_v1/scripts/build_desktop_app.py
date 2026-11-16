#!/usr/bin/env python3
"""
Cross-Platform Build Script for ROV Ground Station Desktop Application.
Self-Bootstrapping:
  - If executed with system Python, it automatically detects/creates the local 'venv',
    ensures PyInstaller is installed in that venv, and re-launches itself inside the venv.
  - Avoids 'externally-managed-environment' errors on modern Linux (Ubuntu 24.04+).
  - Cross-platform: works seamlessly on Linux, macOS, and Windows.

Usage:
  python3 scripts/build_desktop_app.py   (Linux / macOS)
  python scripts\build_desktop_app.py    (Windows)
"""

import os
import sys
import subprocess
import platform

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)


def get_venv_paths():
    """Returns (venv_dir, venv_python) for the current operating system."""
    venv_dir = os.path.join(PROJECT_ROOT, "venv")
    if platform.system() == "Windows":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python3")
        if not os.path.exists(venv_python):
            venv_python = os.path.join(venv_dir, "bin", "python")
    return venv_dir, venv_python


def ensure_virtual_environment():
    """
    Checks if we are running inside the project's virtual environment.
    If not, ensures the venv exists with all dependencies and re-executes.
    """
    venv_dir, venv_python = get_venv_paths()

    # Foolproof standard Python check: sys.prefix != sys.base_prefix inside venv
    is_in_project_venv = (sys.prefix != sys.base_prefix) and (os.path.abspath(sys.prefix) == os.path.abspath(venv_dir))

    if is_in_project_venv:
        # We are inside the venv: ensure PyInstaller is installed inside this venv
        try:
            import PyInstaller
            return
        except ImportError:
            print("[SETUP] Installing PyInstaller into virtual environment...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            return

    # If NOT in project venv: create venv if missing
    if not os.path.exists(venv_dir) or not os.path.exists(venv_python):
        print("=" * 60)
        print("[SETUP] Local virtual environment not found. Creating 'venv'...")
        print("=" * 60)
        subprocess.check_call([sys.executable, "-m", "venv", venv_dir])

    # Ensure pip, requirements, and PyInstaller are installed inside the venv
    print("[SETUP] Verifying dependencies & PyInstaller inside 'venv'...")
    req_file = os.path.join(SCRIPT_DIR, "requirements.txt")
    if os.path.exists(req_file):
        subprocess.check_call([venv_python, "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
        subprocess.check_call([venv_python, "-m", "pip", "install", "-r", req_file, "--quiet"])
    subprocess.check_call([venv_python, "-m", "pip", "install", "pyinstaller", "--quiet"])

    # Re-launch this script using the venv Python
    print(f"[EXEC] Re-launching build under virtual environment ({venv_python})...\n")
    ret = subprocess.call([venv_python, os.path.abspath(__file__)] + sys.argv[1:])
    sys.exit(ret)


def main():
    # 1. Self-bootstrap into virtual environment
    ensure_virtual_environment()

    # 2. Change working directory to project root
    os.chdir(PROJECT_ROOT)
    system = platform.system()
    print("=" * 60)
    print(f" Building ROV Ground Station for {system} ({platform.machine()}) ")
    print("=" * 60)

    import PyInstaller
    print(f"[OK] Running with Python: {sys.executable}")
    print(f"[OK] Found PyInstaller version {PyInstaller.__version__}")

    # 3. Execute PyInstaller using spec file in scripts/
    spec_path = os.path.join(SCRIPT_DIR, "ROVGroundStation.spec")
    dist_dir = os.path.join(PROJECT_ROOT, "dist")
    work_dir = os.path.join(PROJECT_ROOT, "build")
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm",
        "--distpath", dist_dir,
        "--workpath", work_dir,
        spec_path
    ]
    print(f"[BUILD] Executing: {' '.join(cmd)}\n")
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
