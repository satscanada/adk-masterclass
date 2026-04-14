# Module 26 — Retail Deposit API Agent

This folder contains a standalone multi-step sequential ADK agent and its own FastAPI wrapper.

## What is inside

- `agent.py` — `SequentialAgent` with 3 stages:
  - `deposit_intake_agent` (profile + deposits)
  - `deposit_risk_agent` (AML + velocity)
  - `deposit_decision_agent` (strict JSON output)
- `main.py` — direct runner (`run_prompt`) used by CLI/API
- `api_app.py` — standalone FastAPI app for this module only
- `run_retail_deposit_api_server.sh` — start script for the standalone API
- `run_retail_deposit_api.sh` — curl helper for the standalone API

## Run standalone API

From repo root:

```bash
./.venv/bin/python -m uvicorn retail_deposit_api_agent.api_app:app --host 127.0.0.1 --port 8626 --reload
```

Or use the helper script:

```bash
./retail_deposit_api_agent/run_retail_deposit_api_server.sh
```

Endpoints:

- `GET /health`
- `POST /chat`

## Invoke with curl script

From repo root:

```bash
./retail_deposit_api_agent/run_retail_deposit_api.sh RET-3101
./retail_deposit_api_agent/run_retail_deposit_api.sh RET-4420
```

## Raw curl example

```bash
curl -sS http://127.0.0.1:8626/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "RET-3101",
    "user_id": "curl-user"
  }'
```
