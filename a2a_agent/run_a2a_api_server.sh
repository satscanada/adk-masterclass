#!/usr/bin/env bash

set -euo pipefail

HOST="${HOST:-127.0.0.1}"
# Override default: PORT=9000 ./a2a_agent/run_a2a_api_server.sh
# Or: MODULE12_API_PORT=9000 ./a2a_agent/run_a2a_api_server.sh
PORT="${PORT:-${MODULE12_API_PORT:-8726}}"

cd "$(dirname "$0")/.."
./.venv/bin/python -m uvicorn a2a_agent.api_app:app --host "${HOST}" --port "${PORT}" --reload

