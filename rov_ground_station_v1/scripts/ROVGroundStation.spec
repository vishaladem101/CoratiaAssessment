# -*- mode: python ; coding: utf-8 -*-
# ==============================================================================
# ROV Telemetry Ground Station - PyInstaller Spec File
# Cross-Platform: Windows (.exe), Linux (ELF), macOS (.app)
# ==============================================================================

import os
import sys

block_cipher = None

# Resolve absolute paths from spec location
SPECPATH = os.path.dirname(os.path.abspath(SPEC)) if 'SPEC' in locals() else os.getcwd()
PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))

added_files = [
    (os.path.join(PROJECT_ROOT, 'assets', 'map_view.html'), 'assets'),
    (os.path.join(PROJECT_ROOT, 'assets', 'leaflet.js'), 'assets'),
    (os.path.join(PROJECT_ROOT, 'assets', 'leaflet.css'), 'assets'),
    (os.path.join(PROJECT_ROOT, 'assets', 'rov_icon.png'), 'assets'),
    (os.path.join(PROJECT_ROOT, 'assets', 'down_arrow.svg'), 'assets'),
    (os.path.join(PROJECT_ROOT, 'assets', 'tiles'), 'assets/tiles'),
    (os.path.join(PROJECT_ROOT, 'assets', 'map_view.html'), '.'),
    (os.path.join(PROJECT_ROOT, 'assets', 'leaflet.js'), '.'),
    (os.path.join(PROJECT_ROOT, 'assets', 'leaflet.css'), '.'),
    (os.path.join(PROJECT_ROOT, 'assets', 'rov_icon.png'), '.'),
    (os.path.join(PROJECT_ROOT, 'assets', 'down_arrow.svg'), '.'),
    (os.path.join(PROJECT_ROOT, 'assets', 'tiles'), 'tiles')
]

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[PROJECT_ROOT, os.path.join(PROJECT_ROOT, 'src')],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
        'pyqtgraph',
        'numpy',
        'src.joystick_controller'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ROVGroundStation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Windowed GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ROVGroundStation'
)

