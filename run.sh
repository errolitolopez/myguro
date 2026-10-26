#!/usr/bin/env bash
# Start myguro. Sets everything up the first time.
#
#   ./run.sh          run on this computer only (http://127.0.0.1:5000)
#   ./run.sh lan      also reachable from other devices on the same Wi-Fi
#   ./run.sh check    only check that every package in requirements.txt is installed, for the virtual
#                     environment here or for another Python: PYTHON=python3.12 ./run.sh check

set -e
cd "$(dirname "$0")"

# Prints each package from requirements.txt that is missing or has another version than the pinned one
# for the Python given ($1), and fails if there is any. "Installed for another Python version" looks the
# same as "missing" here, which is the point: the app only sees the packages of the Python that runs it.
check_requirements() {
  "$1" - <<'PY'
import re
import sys
from importlib.metadata import PackageNotFoundError, version

problems = []
for line in open("requirements.txt"):
    pinned = re.match(r"([A-Za-z0-9_.-]+)==(\S+)$", line.split("#")[0].strip())
    if not pinned:
        continue
    name, wanted = pinned.groups()
    try:
        found = version(name)
    except PackageNotFoundError:
        problems.append(f"  {name} is missing (needs {wanted})")
        continue
    if found != wanted:
        problems.append(f"  {name} is {found} (needs {wanted})")
if problems:
    print("\n".join(problems))
    sys.exit(1)
PY
}

# ./run.sh check: no setup and no start, just the check (use PYTHON=... for a Python without the .venv)
if [ "$1" = "check" ]; then
  python="${PYTHON:-}"
  if [ -z "$python" ]; then
    if [ -x .venv/bin/python ]; then python=.venv/bin/python; else python=python3; fi
  fi
  if check_requirements "$python"; then
    echo "All requirements are installed for $($python --version)."
    exit 0
  fi
  echo "Install them with: $python -m pip install -r requirements.txt (add --user outside a virtual environment)" >&2
  exit 1
fi

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
# The marker only says pip ran once. Check the packages really are there for this Python, and install
# again once if not (for example a damaged .venv); stop with a clear message if that does not fix it.
if ! check_requirements .venv/bin/python >/dev/null; then
  echo "Some requirements are missing. Installing again..."
  .venv/bin/pip install -q -r requirements.txt
  if ! check_requirements .venv/bin/python; then
    echo "The requirements above could not be installed. Check your internet connection and try again." >&2
    exit 1
  fi
fi

# 2. The Gemini key for the navigation chatbot, if ./set-gemini-key.sh saved one
if [ -f instance/gemini.env ]; then
  . instance/gemini.env
fi

# 3. Start the app (the database and the default admin are created on first start)
if [ "$1" = "lan" ]; then
  ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  echo "Open on other devices: http://${ip:-<your-computer-ip>}:5000"
  # No --debug here: the debugger must never be reachable from other devices.
  exec .venv/bin/flask --app app run --host 0.0.0.0
else
  exec .venv/bin/flask --app app run --debug
fi
