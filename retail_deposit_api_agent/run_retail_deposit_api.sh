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

MODULE26_CHAT_RAW="${response}" python3 <<'PY'
import json
import os

raw = os.environ.get("MODULE26_CHAT_RAW", "")

try:
    envelope = json.loads(raw)
except json.JSONDecodeError:
    print(raw, end="" if raw.endswith("\n") else "\n")
    raise SystemExit(0)

agent_key = envelope.get("agent_key", "n/a")
session_id = envelope.get("session_id", "n/a")
inner = envelope.get("response", "")

print(f"agent_key: {agent_key}")
print(f"session_id: {session_id}")
print("response:")

if isinstance(inner, str):
    try:
        parsed = json.loads(inner)
        print(json.dumps(parsed, indent=2, sort_keys=True, ensure_ascii=False))
    except json.JSONDecodeError:
        print(inner.rstrip("\n"))
elif isinstance(inner, (dict, list)):
    print(json.dumps(inner, indent=2, sort_keys=True, ensure_ascii=False))
else:
    print(inner)
PY

echo
