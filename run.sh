#!/usr/bin/env bash
set -euo pipefail

# Usage: ./run.sh   or   ./run.sh start   (start is optional, for muscle memory)
# Expose Vite on the LAN: VITE_DEV_HOST=0.0.0.0 ./run.sh
# Help: ./run.sh help

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

case "${1:-}" in
  -h|--help|help)
    echo "Usage: ./run.sh [start]"
    echo "  Starts Agent API on http://127.0.0.1:8512 and Vite on port 8513 (see ui/.env)."
    echo ""
    echo "Environment:"
    echo "  LOG_LEVEL=debug          Lower uvicorn log noise threshold"
    echo "  VITE_DEV_HOST=0.0.0.0    Listen on all interfaces (Vite \"Network\" URL)"
    exit 0
    ;;
  start|'')
    ;;
  *)
    echo "Unknown argument: $1 (try: ./run.sh help)" >&2
    exit 1
    ;;
esac

# Free a TCP port so a previous dev session (or stray process) does not block bind.
# Uses lsof (macOS + typical Linux). Safe with set -e: empty lsof must not abort.
free_port() {
  local port="$1"
  local label="${2:-port ${port}}"
  local pids

  pids=$(lsof -nP -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null || true)
  if [[ -z "${pids}" ]]; then
    return 0
  fi

  echo "Stopping ${label} (freeing TCP ${port}, PIDs: ${pids//[$'\n']/ })..."
  kill ${pids} 2>/dev/null || true
  sleep 0.5
  pids=$(lsof -nP -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null || true)
  if [[ -n "${pids}" ]]; then
    echo "  Force killing still listening on ${port}: ${pids//[$'\n']/ }"
    kill -9 ${pids} 2>/dev/null || true
  fi
}

# Wait until the FastAPI process is accepting connections so Vite's proxy does not race.
wait_for_agent_api() {
  local max_attempts=80
  local i=0
  echo "Waiting for Agent API to accept connections..."
  while [[ $i -lt $max_attempts ]]; do
    if curl -sf "http://127.0.0.1:8512/health" >/dev/null 2>&1; then
      echo "  Agent API is ready."
      return 0
    fi
    sleep 0.25
    i=$((i + 1))
  done
  echo "Error: timed out waiting for http://127.0.0.1:8512/health (is curl installed?)" >&2
  return 1
}

clear

echo "Checking for stale listeners (same ports as this script)..."
free_port 8512 "Agent API (uvicorn)"
free_port 8513 "React UI (Vite)"
echo ""

uvicorn_pid=""
vite_pid=""
_cleanup_done=""

cleanup() {
  [[ -n "${_cleanup_done:-}" ]] && return
  _cleanup_done=1

  # Vite runs under npm; kill children first so the dev server does not linger.
  if [[ -n "${vite_pid}" ]]; then
    pkill -P "${vite_pid}" 2>/dev/null || true
    kill "${vite_pid}" 2>/dev/null || true
  fi
  if [[ -n "${uvicorn_pid}" ]]; then
    kill "${uvicorn_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# Default log level: INFO (uvicorn + Python loggers). Override: LOG_LEVEL=debug ./run.sh
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
_uvicorn_log_level="$(printf '%s' "${LOG_LEVEL}" | tr '[:upper:]' '[:lower:]')"

./.venv/bin/python -m uvicorn api_app:app --host 127.0.0.1 --port 8512 --log-level "${_uvicorn_log_level}" &
uvicorn_pid=$!

if ! wait_for_agent_api; then
  exit 1
fi

(cd "${ROOT}/ui" && npm run dev) &
vite_pid=$!

echo ""
echo "  Agent API (FastAPI):  http://127.0.0.1:8512"
echo "  React UI (Vite):      http://localhost:8513"
if [[ -n "${VITE_DEV_HOST:-}" ]]; then
  echo "  (VITE_DEV_HOST=${VITE_DEV_HOST} — check terminal for Network URL)"
fi
echo ""

wait
