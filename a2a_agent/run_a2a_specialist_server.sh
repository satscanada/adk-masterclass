#!/usr/bin/env bash

set -euo pipefail

HOST="${HOST:-127.0.0.1}"
# Override default: PORT=8830 ./a2a_agent/run_a2a_specialist_server.sh
# Or: MODULE12_SPECIALIST_PORT=8830 ./a2a_agent/run_a2a_specialist_server.sh
PORT="${PORT:-${MODULE12_SPECIALIST_PORT:-8720}}"

cd "$(dirname "$0")/.."
./.venv/bin/python -m uvicorn a2a_agent.specialist_api:app --host "${HOST}" --port "${PORT}" --reload

