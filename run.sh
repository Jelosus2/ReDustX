#!/usr/bin/env bash
set -euo pipefail

# Change to the directory of this script
cd "$(dirname "$0")"

VENV_DIR="venv"
ENTRY_FILE="ReDustX.py"

if [[ ! -f "${VENV_DIR}/bin/python" ]]; then
  echo
  echo "Virtual environment not found at \"${VENV_DIR}\"."
  echo "Please run ./install.sh first to set up dependencies."
  echo
  exit 1
fi

exec "${VENV_DIR}/bin/python" "${ENTRY_FILE}"
