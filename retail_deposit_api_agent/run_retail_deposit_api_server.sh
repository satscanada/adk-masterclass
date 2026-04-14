#!/usr/bin/env bash

set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8626}"
RELOAD_FLAG="${RELOAD_FLAG:---reload}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "Starting Module 26 standalone API server..."
echo "  HOST: ${HOST}"
echo "  PORT: ${PORT}"
echo

./.venv/bin/python -m uvicorn retail_deposit_api_agent.api_app:app --host "${HOST}" --port "${PORT}" ${RELOAD_FLAG}
