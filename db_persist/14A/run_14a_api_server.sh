#!/usr/bin/env bash

set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-${MODULE14A_API_PORT:-8740}}"

cd "$(dirname "$0")/../.."
./.venv/bin/python -m uvicorn db_persist.14A.api_app:app --host "${HOST}" --port "${PORT}" --reload
