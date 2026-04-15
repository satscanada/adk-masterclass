# Module 13 — Session Management (In-Memory) Use Case

This folder contains a retail deposit banking use case designed specifically to demonstrate **Module 13: Session Management — In-Memory**.

## What we cover in Module 13

This lesson focuses on a practical, beginner-friendly retail deposit workflow using ADK `SequentialAgent` + `InMemorySessionService`:

- **Intake analysis** — gather customer profile and recent deposit behavior.
- **Risk checks** — run AML and transaction velocity checks on the same customer.
- **Decisioning pattern** — produce a clear recommendation with next actions.
- **State handoff across stages** — each specialist writes context used by the next specialist.
- **Session memory behavior** — with the same `session_id`, follow-up turns can reuse the previously supplied customer ID.
- **API/UI integration** — register once in `agents.json` and run from shared FastAPI + React chat UI.
- **Deterministic teaching scenarios** — compare outcomes using `RET-3101` (healthy) vs `RET-4420` (higher-risk).

## What is inside

- `agent.py` — `SequentialAgent` with 3 stages:
  - `retail_intake_agent` (profile + deposit intake snapshot)
  - `retail_risk_agent` (AML + velocity checks)
  - `retail_offer_agent` (final recommendation + next actions)
- `main.py` — module runner (`run_prompt`) for CLI and shared API registration

## Run from CLI

From repo root:

```bash
./.venv/bin/python -m retail_deposit_banking_agent.main RET-3101
./.venv/bin/python -m retail_deposit_banking_agent.main RET-4420
```

## In-memory session demo (shared API)

Use the same `session_id` across turns:

```bash
# Turn 1: provide customer ID explicitly
curl -sS http://127.0.0.1:8512/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "retail_deposit_banking_agent",
    "prompt": "RET-3101",
    "user_id": "memory-demo",
    "session_id": "module13-session-1"
  }'

# Turn 2: omit customer ID; module reuses last customer from in-memory session context
curl -sS http://127.0.0.1:8512/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "retail_deposit_banking_agent",
    "prompt": "Re-evaluate and give a stricter risk summary.",
    "user_id": "memory-demo",
    "session_id": "module13-session-1"
  }'
```

## Shared API / UI

This module is wired through `agents.json` as `retail_deposit_banking_agent`.

- API route: `POST /api/chat`
- React UI: pick **Retail Deposit Banking (Module 13)** and send `RET-3101` or `RET-4420`.

