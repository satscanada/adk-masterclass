#!/usr/bin/env bash

set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8626}"
CUSTOMER_ID="${1:-RET-3101}"
USER_ID="${2:-curl-user}"

echo "Calling Module 26 standalone API..."
echo "  API_BASE:    ${API_BASE}"
echo "  CUSTOMER_ID: ${CUSTOMER_ID}"
echo "  USER_ID:     ${USER_ID}"
echo

response="$(
  curl -sS "${API_BASE}/chat" \
    -H "Content-Type: application/json" \
    -d "{
      \"prompt\": \"${CUSTOMER_ID}\",
      \"user_id\": \"${USER_ID}\"
    }"
)"

if command -v jq >/dev/null 2>&1; then
  if echo "${response}" | jq -e . >/dev/null 2>&1; then
    echo "${response}" | jq .
  else
    printf '%s\n' "${response}"
  fi
else
  if echo "${response}" | python3 -m json.tool >/dev/null 2>&1; then
    echo "${response}" | python3 -m json.tool
  else
    printf '%s\n' "${response}"
  fi
fi

echo
