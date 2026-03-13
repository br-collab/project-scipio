#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/restart_server.sh [port]
# Kills any process listening on the port, (re)starts app.py using the
# project's .venv Python, and writes logs to logs/server.log.

PORT="${1:-8000}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"
mkdir -p logs

echo "Restarting server on port $PORT..."
pids=$(lsof -ti tcp:$PORT || true)
if [ -n "$pids" ]; then
  echo "Killing processes on port $PORT: $pids"
  kill -9 $pids || true
fi

if [ -f .venv/bin/activate ]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

# Use the flask CLI to run the app on the requested port without the reloader.
# This respects the app factory and avoids re-import/reloader issues.
export FLASK_APP=app.py
export FLASK_ENV=development
nohup .venv/bin/python -m flask run --host=127.0.0.1 --port="$PORT" --no-reload > logs/server.log 2>&1 & echo $! > .server_pid
echo "Server started (pid $(cat .server_pid)). Logs: logs/server.log"
