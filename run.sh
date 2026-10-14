#!/usr/bin/env bash
# One command to install everything and start the service on port 8000.
set -e
cd "$(dirname "$0")"

if [ ! -f requirements.txt ]; then
  echo "ERROR: requirements.txt not found in $(pwd)"
  exit 1
fi

# 1. Find Python 3.
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi

# 2. Create a private environment, unless one already exists.
if [ ! -d .venv ]; then
  "$PY" -m venv .venv || echo "Could not create .venv; installing for this user instead."
fi

# 3. Use the environment's own Python if it was created.
#    Without a venv, install for the current user instead.
USER_FLAG="--user"
if   [ -x .venv/bin/python ];         then PY=.venv/bin/python;         USER_FLAG=""
elif [ -x .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe; USER_FLAG=""
fi

# 4. Install the libraries, then start the server.
"$PY" -m pip install --quiet --disable-pip-version-check $USER_FLAG -r requirements.txt
exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000