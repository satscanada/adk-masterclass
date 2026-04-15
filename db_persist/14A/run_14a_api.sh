#!/usr/bin/env bash

set -euo pipefail

MODULE14A_API_PORT="${MODULE14A_API_PORT:-8740}"
API_BASE="${API_BASE:-http://127.0.0.1:${MODULE14A_API_PORT}}"
PROMPT="${1:-CUST-3001}"
USER_ID="${2:-curl-user}"
SESSION_ID="${3:-}"
WEEK="${4:-}"
CATEGORY="${5:-}"
AMOUNT="${6:-}"
RESPONSE="${7:-}"   # accepted | declined | not_now

echo "Calling Module 14A Spending Coach API..."
echo "  API_BASE:   ${API_BASE}"
echo "  Usage:      ./db_persist/14A/run_14a_api.sh [prompt] [user_id] [session_id] [week] [category] [amount] [response]"
echo "  PROMPT:     ${PROMPT}"
echo "  USER_ID:    ${USER_ID}"
if [[ -n "${SESSION_ID}" ]]; then
  echo "  SESSION_ID: ${SESSION_ID}"
fi
if [[ -n "${WEEK}" || -n "${CATEGORY}" || -n "${AMOUNT}" ]]; then
  echo "  WEEK:       ${WEEK:-<none>}"
  echo "  CATEGORY:   ${CATEGORY:-<none>}"
  echo "  AMOUNT:     ${AMOUNT:-<none>}"
fi
if [[ -n "${RESPONSE}" ]]; then
  echo "  RESPONSE:   ${RESPONSE}"
fi
echo
payload="{\"prompt\":\"${PROMPT}\",\"user_id\":\"${USER_ID}\""
if [[ -n "${SESSION_ID}" ]]; then
  payload="${payload},\"session_id\":\"${SESSION_ID}\""
fi
if [[ -n "${WEEK}" ]]; then
  payload="${payload},\"week\":\"${WEEK}\""
fi
if [[ -n "${CATEGORY}" ]]; then
  payload="${payload},\"category\":\"${CATEGORY}\""
fi
if [[ -n "${AMOUNT}" ]]; then
  payload="${payload},\"amount\":${AMOUNT}"
fi
if [[ -n "${RESPONSE}" ]]; then
  payload="${payload},\"customer_response\":\"${RESPONSE}\""
fi
payload="${payload}}"

curl -sS "${API_BASE}/chat" \
  -H "Content-Type: application/json" \
  -d "${payload}" | python3 -m json.tool

echo
