# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the heka2abf GUI.

Why a spec (not just CLI flags):
  * heka_reader is a vendored SINGLE-FILE module, not a package. It is
    normally copied into site-packages via install.bat, so PyInstaller's
    static analysis never finds it. We bundle it as a top-level module by
    (1) adding third_party/ to pathex so analysis finds heka_reader.py and
    (2) listing it in hiddenimports so it survives bundle pruning.
  * numpy + tkinter: PyInstaller detects these automatically.
  * --windowed: GUI app, no console window.

Build:
    .venv\\Scripts\\pyinstaller build\\heka2abf-gui.spec --noconfirm

Output:
    dist\\heka2abf-gui\\heka2abf-gui.exe   (default --onedir; faster startup)
    OR with --onefile: a single dist\\heka2abf-gui.exe
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).resolve().parent  # SPECPATH is injected by PyInstaller
THIRD_PARTY  = PROJECT_ROOT / "third_party"
ENTRY        = PROJECT_ROOT / "heka2abf" / "gui.py"

block_cipher = None

a = Analysis(
    [str(ENTRY)],
    pathex=[
        str(PROJECT_ROOT),
        str(THIRD_PARTY),  # so Analysis finds heka_reader.py
    ],
    binaries=[],
    datas=[
        # README bundled next to the exe so the "Help" / "About" dialogs
        # can reference docs if you ever want to display them.
        (str(PROJECT_ROOT / "README.md"), "."),
    ],
    hiddenimports=[
        "heka_reader",     # vendored single-file module, not on PyPI
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim a few heavy modules heka2abf never imports.
        "matplotlib", "pandas", "scipy", "IPython", "jupyter",
        "pytest", "setuptools", "wheel",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- onefile ---
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="heka2abf-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                # don't run UPX — antivirus false-positives get worse
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # GUI — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)