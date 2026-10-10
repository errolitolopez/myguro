#!/usr/bin/env bash
# Start myguro. Sets everything up the first time.
#
#   ./run.sh          run on this computer only (http://127.0.0.1:5000)
#   ./run.sh lan      also reachable from other devices on the same Wi-Fi

set -e
cd "$(dirname "$0")"

# 1. Virtual environment + dependencies (only installs when requirements.txt changes)
if [ ! -d .venv ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi
if [ ! -f .venv/.installed ] || [ requirements.txt -nt .venv/.installed ]; then
  echo "Installing dependencies..."
  .venv/bin/pip install -q -r requirements.txt
  touch .venv/.installed
fi

# 2. Start the app (the database and the default admin are created on first start)
if [ "$1" = "lan" ]; then
  ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  echo "Open on other devices: http://${ip:-<your-computer-ip>}:5000"
  # No --debug here: the debugger must never be reachable from other devices.
  exec .venv/bin/flask --app app run --host 0.0.0.0
else
  exec .venv/bin/flask --app app run --debug
fi
