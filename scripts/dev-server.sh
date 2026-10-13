#!/usr/bin/env bash
# Manage the local Flask dev server (127.0.0.1 only, per constitution).
set -euo pipefail

cd "$(dirname "$0")/.."

# 5001, not 5000: macOS AirPlay Receiver (ControlCenter) squats on port 5000
# whenever nothing else is bound to it, so a stopped dev server gets silently
# replaced by AirPlay and requests 403 instead of connection-refusing.
PORT="${BUDGET_DEV_PORT:-5001}"
LOG_FILE=".dev-server.log"

find_pid() {
  # `|| true`: lsof exits non-zero when nothing matches, which under
  # `set -eo pipefail` would otherwise silently kill this script the instant
  # nothing is listening on $PORT (previously masked on port 5000, since
  # something — AirPlay Receiver — was always listening there).
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | awk '$1 == "Python" {print $2; exit}' || true
}

start() {
  local pid
  pid="$(find_pid)"
  if [ -n "$pid" ]; then
    echo "Already running on http://127.0.0.1:$PORT (PID $pid)"
    return 0
  fi
  source .venv/bin/activate
  export BUDGET_ENV=development
  export PGDATABASE="${PGDATABASE:-budget_dev}"
  nohup flask --app src.budget.app run --port "$PORT" > "$LOG_FILE" 2>&1 &
  disown
  sleep 3
  pid="$(find_pid)"
  if [ -z "$pid" ]; then
    echo "Failed to start — check $LOG_FILE" >&2
    exit 1
  fi
  echo "Started on http://127.0.0.1:$PORT (PID $pid)"
}

stop() {
  local pid
  pid="$(find_pid)"
  if [ -z "$pid" ]; then
    echo "Not running on port $PORT"
    return 0
  fi
  kill "$pid"
  sleep 1
  echo "Stopped (PID $pid)"
}

restart() {
  stop
  start
}

status() {
  local pid
  pid="$(find_pid)"
  if [ -n "$pid" ]; then
    echo "Running on http://127.0.0.1:$PORT (PID $pid)"
  else
    echo "Not running"
  fi
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) restart ;;
  status) status ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}" >&2
    exit 1
    ;;
esac
