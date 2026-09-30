# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the heka2abf GUI, --onedir mode.

Difference from heka2abf-gui.spec:
  * onedir produces a FOLDER (dist\heka2abf-gui\) containing:
      - heka2abf-gui.exe (small bootloader, ~few MB)
      - _internal\... (Python + numpy + tkinter + data)
  * Startup is INSTANT (no %TEMP% extraction).
  * Folder can be zipped for distribution; total ~50-60 MB.
  * AV false positives much rarer than --onefile (no self-extract tricks).

Tradeoff vs --onefile:
  + Faster startup (~0.5s vs ~3-5s)
  + Less AV false positives
  + Easier to debug (can inspect _internal/)
  - Multiple files to ship (zip the folder)
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).resolve().parent
THIRD_PARTY  = PROJECT_ROOT / "third_party"
ENTRY        = PROJECT_ROOT / "heka2abf" / "gui.py"

block_cipher = None

a = Analysis(
    [str(ENTRY)],
    pathex=[str(PROJECT_ROOT), str(THIRD_PARTY)],
    binaries=[],
    datas=[(str(PROJECT_ROOT / "README.md"), ".")],
    hiddenimports=["heka_reader"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "pandas", "scipy", "IPython", "jupyter",
        "pytest", "setuptools", "wheel",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- onedir: small EXE + COLLECT for everything else ---
exe = EXE(
    pyz,
    a.scripts,           # only the entry script goes into the EXE
    [],                  # binaries/zipfiles/datas go to COLLECT, not EXE
    name="heka2abf-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,       # GUI, no console window
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="heka2abf-gui",
)