#!/usr/bin/env bash
# Manage the local Flask dev server (127.0.0.1 only, per constitution).
set -euo pipefail

cd "$(dirname "$0")/.."

PORT="${BUDGET_DEV_PORT:-5000}"
LOG_FILE=".dev-server.log"

find_pid() {
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | awk '$1 == "Python" {print $2; exit}'
}

start() {
  local pid
  pid="$(find_pid)"
  if [ -n "$pid" ]; then
    echo "Already running on http://127.0.0.1:$PORT (PID $pid)"
    return 0
  fi
  source .venv/bin/activate
  nohup flask --app src.budget.app run --port "$PORT" > "$LOG_FILE" 2>&1 &
  disown
  sleep 1
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
