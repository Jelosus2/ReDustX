#!/usr/bin/env bash
set -euo pipefail

# Change to the directory of this script
cd "$(dirname "$0")"

VENV_DIR="venv"
REQ_FILE="requirements.txt"
ENTRY_FILE="ReDustX.py"

echo "=== ReDustX setup ==="

# Detect a usable Python 3
PY_CMD=""
if command -v python3 >/dev/null 2>&1; then
  PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  if python - <<'PY'
import sys
raise SystemExit(0 if sys.version_info.major >= 3 else 1)
PY
  then
    PY_CMD="python"
  fi
fi

if [[ -z "${PY_CMD}" ]]; then
  echo
  echo "Python 3 is not installed or not on PATH."
  echo "Please install Python 3 using your package manager (e.g. apt, dnf, pacman)."
  echo "On Debian/Ubuntu, you may need: sudo apt update && sudo apt install python3 python3-venv"
  exit 1
fi

# Create virtual environment if it doesn't exist
if [[ ! -f "${VENV_DIR}/bin/python" ]]; then
  echo "Creating virtual environment in \"${VENV_DIR}\"..."
  if ! ${PY_CMD} -m venv "${VENV_DIR}"; then
    echo "Failed to create virtual environment."
    echo "On Debian/Ubuntu, install: sudo apt install python3-venv"
    exit 1
  fi
fi

if [[ -f "${REQ_FILE}" ]]; then
  if ! "${VENV_DIR}/bin/python" -m pip install -r "${REQ_FILE}"; then
    echo "Failed to install dependencies from ${REQ_FILE}."
    exit 1
  fi
else
  echo "Warning: ${REQ_FILE} not found. Skipping dependency install."
fi

echo
echo "Setup complete. Launching ReDustX..."
exec bash ./run.sh
