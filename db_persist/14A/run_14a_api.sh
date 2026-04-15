#!/usr/bin/env bash

set -euo pipefail

MODULE14A_API_PORT="${MODULE14A_API_PORT:-8740}"
API_BASE="${API_BASE:-http://127.0.0.1:${MODULE14A_API_PORT}}"
PROMPT="${1:-CUST-3001}"
USER_ID="${2:-curl-user}"
SESSION_ID="${3:-}"

echo "Calling Module 14A Spending Coach API..."
echo "  API_BASE:   ${API_BASE}"
echo "  PROMPT:     ${PROMPT}"
echo "  USER_ID:    ${USER_ID}"
if [[ -n "${SESSION_ID}" ]]; then
  echo "  SESSION_ID: ${SESSION_ID}"
fi
echo

if [[ -n "${SESSION_ID}" ]]; then
  payload="{
    \"prompt\": \"${PROMPT}\",
    \"user_id\": \"${USER_ID}\",
    \"session_id\": \"${SESSION_ID}\"
  }"
else
  payload="{
    \"prompt\": \"${PROMPT}\",
    \"user_id\": \"${USER_ID}\"
  }"
fi

curl -sS "${API_BASE}/chat" \
  -H "Content-Type: application/json" \
  -d "${payload}" | python3 -m json.tool

echo
