#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Free a TCP port so a previous Streamlit session does not block bind.
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

clear

echo "Checking for stale Streamlit listener..."
free_port 8511 "Streamlit"
echo ""

echo "  Streamlit:  http://localhost:8511"
echo ""

./.venv/bin/streamlit run streamlit_app.py \
  --server.headless true \
  --server.port 8511 \
  --browser.gatherUsageStats false \
  --server.runOnSave true \
  --server.fileWatcherType auto
