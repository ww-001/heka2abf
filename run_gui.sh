#!/usr/bin/env bash
# Launch the heka2abf GUI using the venv Python (Linux / macOS).
#
# Usage:  ./run_gui.sh
#
# If .venv doesn't exist yet, this script will offer to run ./install.sh
# for you.

set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo ".venv not found.  Run ./install.sh first to set up the environment."
  echo "Attempting to run ./install.sh now..."
  exec ./install.sh
fi

VPY="./.venv/bin/python"
if [ ! -x "$VPY" ]; then
  echo "ERROR: .venv/bin/python not executable. Re-run ./install.sh." >&2
  exit 1
fi

exec "$VPY" "$(dirname "$0")/heka2abf/gui.py"