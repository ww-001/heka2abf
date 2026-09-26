#!/usr/bin/env bash
# Install heka2abf into an isolated virtualenv (Linux / macOS).
#
# Usage:  ./install.sh
#
# Creates ./.venv/ with Python 3.9+, installs numpy + pyabf, and copies
# third_party/heka_reader.py into the venv's site-packages (heka_reader
# is not on PyPI; vendored single-file module).
#
# After install:  ./run_gui.sh   to launch the GUI
#                 heka2abf       to use the CLI
#                 pytest tests/test_abf2writer.py -v   to run synthetic tests

set -euo pipefail

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found in PATH. Install Python 3.9+ first." >&2
  exit 1
fi

PY_VER="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
PY_MAJOR="$(echo "$PY_VER" | cut -d. -f1)"
PY_MINOR="$(echo "$PY_VER" | cut -d. -f2)"
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
  echo "ERROR: Python $PY_VER is too old. Need Python 3.9+." >&2
  exit 1
fi

echo "[1/4] Creating virtual environment ./.venv ..."
python3 -m venv .venv

VPY="./.venv/bin/python"

echo "[2/4] Upgrading pip and installing numpy + pyabf ..."
"$VPY" -m pip install --upgrade pip
"$VPY" -m pip install numpy pyabf

echo "[3/4] Copying vendored heka_reader.py into the venv ..."
# Discover the actual site-packages directory.
SITE_DIR="$("$VPY" -c 'import site; print(site.getsitepackages()[0])')"
cp third_party/heka_reader.py "$SITE_DIR/heka_reader.py"

echo "[4/4] Done."
echo
echo "Next:"
echo "  ./run_gui.sh                                  # launch the GUI"
echo "  source .venv/bin/activate && heka2abf --help  # CLI"
echo "  source .venv/bin/activate && pytest tests/test_abf2writer.py -v"