# heka2abf — Windows Bundle Quick Start

> **For colleagues who don't want to install Python themselves.**
>
> This is a pre-built `.zip` containing the full `heka2abf` project **plus a
> ready-made Python virtual environment** (`.venv/`) with `numpy` and the
> HEKA `.dat` parser already installed. No Python install, no `pip install`,
> no setup. Just unzip and double-click.

---

## 🚀 30-second setup

1. **Unzip** `heka2abf_windows_vX.Y.Z.zip` to any folder
   (e.g. `D:\tools\heka2abf\`).
2. **Open** the unzipped folder in File Explorer.
3. **Double-click** `run_gui.bat`.
4. The GUI launches — no console window, no prompts. Ready to convert.

That's it. No Python to install. No `pip install` to run. No `git clone`.

---

## 📋 What's inside the bundle

```
heka2abf/
├── run_gui.bat              ← double-click this to launch the GUI
├── run_gui_console.bat      ← same but shows the console (for debugging)
├── install.bat              ← re-creates .venv from scratch (rarely needed)
├── heka2abf/                ← the Python package source
├── tests/                   ← reference test data + test scripts (optional)
├── reference/               ← sample Clampfit ABF2 files (for cross-checking)
├── third_party/
│   └── heka_reader.py       ← vendored HEKA parser
├── tools/
│   └── abf2_dump.py         ← ABF2 hex-dumper (for debugging)
├── docs/
│   └── screenshot.png       ← GUI screenshot
├── README.md, LICENSE, ...  ← standard repo files
└── .venv/                   ← bundled Python venv (numpy + heka_reader preinstalled)
    └── Scripts/python.exe
```

---

## ❓ FAQ

### Q: My colleague doesn't have Python installed at all. Will this still work?
**A: Yes.** The `.venv/` folder contains a self-contained Python interpreter
plus `numpy` and `heka_reader`. No system Python is required.

### Q: Which Windows versions are supported?
**A: Windows 10 / 11** (primary). The bundled Python is from python.org
(64-bit). The bundle was built on Windows 10 64-bit.

### Q: Can I move the folder after unzipping?
**A: Yes.** The `.venv/` is fully self-contained, no absolute paths, no
registry entries. You can put it anywhere (USB stick, OneDrive sync folder,
network share) — it just runs.

### Q: Antivirus flags the bundle as suspicious — what do I do?
**A: This sometimes happens with PyInstaller-style bundles. Our bundle is
NOT a PyInstaller bundle (it's a plain `.venv/`), so this should not happen.
If it does, add an exclusion for the `heka2abf` folder in your AV settings.

### Q: Conversion fails with "ModuleNotFoundError: No module named 'heka_reader'"?
**A:** Your `.venv/` may have been deleted or corrupted. Re-create it:
1. Install Python 3.9+ (from python.org, tick "Add to PATH")
2. Double-click `install.bat` — it rebuilds `.venv/` and re-copies
   `heka_reader.py` into it.
3. Try `run_gui.bat` again.

### Q: Conversion succeeds but I want to run the bundled tests too.
**A:** Open a Command Prompt in the bundle folder and run:

```
.venv\Scripts\python.exe tests\test_abf2writer.py
```

(`pyabf` is NOT bundled because it's only used by the bundled tests. To run
tests that need `pyabf`, first run `install.bat` then
`.venv\Scripts\pip install pyabf`.)

### Q: How do I uninstall?
**A:** Delete the unzipped folder. Nothing was written to the system, the
registry, or `%APPDATA%`. (The `gui_error.log` file, if any, lives inside the
`heka2abf\heka2abf\` subfolder and is deleted with it.)

---

## 📞 Getting help

If conversion doesn't work, before asking for help please send:

1. The `.dat` filename (or a sample) you're trying to convert
2. The contents of `heka2abf\heka2abf\gui_error.log` (if any)
3. The full log from the GUI's "Log" panel after a failed conversion

This is a free tool maintained by the WWT Lab. Bug reports and PRs are
welcome at https://github.com/ww-001/heka2abf/issues.

---

By: WWT Lab (Wenting Wang's Lab) — MIT License — 2026