#!/bin/bash
# Double-click on macOS to launch Brainy (first run installs everything).
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Première installation de Brainy…"
  PY=""
  for c in python3.13 python3.12 python3.11 python3.10 /opt/homebrew/bin/python3 python3; do
    if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then PY="$c"; break; fi
  done
  [ -n "$PY" ] || { echo "Python 3.10+ requis : brew install python@3.12"; exit 1; }
  "$PY" -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
  .venv/bin/python -m playwright install chromium
fi
if [ ! -f frontend/dist/index.html ]; then
  (cd frontend && npm install --silent && npm run build)
fi
exec .venv/bin/python -m brainy.app "$@"
