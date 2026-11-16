#!/bin/bash
# Starts Prose Clinic.
#   macOS: double-click this file (the first time, right-click it and choose "Open").
#   Linux: run   bash start_mac_linux.command   in a terminal.
# The first run sets things up automatically (needs internet for a minute or two).

cd "$(dirname "$0")" || exit 1

pause_and_exit() {
  echo
  read -r -p "Press Enter to close this window..."
  exit 1
}

PY=""
for candidate in python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    PY="$candidate"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "Prose Clinic needs Python 3.11 or newer, and it wasn't found."
  echo "Install it from https://www.python.org/downloads/ and try again (see README.md)."
  pause_and_exit
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "First run: creating a private Python environment in the .venv folder..."
  "$PY" -m venv .venv || { echo "Couldn't create the environment."; pause_and_exit; }
fi

if ! cmp -s requirements.txt .venv/requirements.installed; then
  echo "Installing the packages Prose Clinic needs (one time only)..."
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  if ! .venv/bin/python -m pip install -r requirements.txt; then
    echo "Installing packages failed. Check your internet connection and run this again."
    pause_and_exit
  fi
  cp requirements.txt .venv/requirements.installed
fi

echo
echo "Starting Prose Clinic. Your browser should open automatically."
echo "If it doesn't, open http://localhost:8501"
echo "To stop the app, close this window (or press Ctrl+C)."
echo
.venv/bin/python -m streamlit run app.py
