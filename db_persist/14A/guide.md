# Module 14A Guide

Module 14A implements a persistent spending-pattern coach using ADK `DatabaseSessionService` with PostgreSQL.

## Use Case

- Input customer IDs: `CUST-3001`, `CUST-3002`, `CUST-3003`
- Stage 1 (`spending_log_agent`) upserts a weekly spend snapshot into `session.state["spending_log"]` (keyed by `customer_id + week`, so re-running the same week updates rather than duplicates)
- Stage 2 (`spending_coaching_agent`) applies deterministic trend detection and a 30-day suppression rule from `session.state["suggestion_history"]`
- The LLM never computes date windows or suppression logic; tools do that deterministically

## PostgreSQL Persistence

- Default DB URL in code:
  - `postgresql+asyncpg://postgres:postgres@127.0.0.1:6433/adk_sessions`
- Override with env var:
  - `MODULE14A_DB_URL=postgresql+asyncpg://<user>:<pass>@127.0.0.1:6433/<db>`
- Default schema target for ADK session tables:
  - `MODULE14A_DB_SCHEMA=adk_module14a`
  - Module 14A sets PostgreSQL `search_path` using asyncpg `server_settings`, so ADK-created tables land in this schema by default.
- Session consolidation mode:
  - `MODULE14A_SESSION_SCOPE=customer` (default)
  - ADK sessions are keyed by `(app_name, user_id, session_id)`. In `customer` mode, Module 14A derives an internal effective user id (`customer::<customer_id>`) so CLI/API calls for the same customer share the same persisted thread even if caller `user_id` differs.
  - Set `MODULE14A_SESSION_SCOPE=user` to restore strict caller-user isolation.
- Stable customer sessions:
  - default `session_id` is `spending-coach-<customer_id>`
- Demo seed behavior:
  - `CUST-3003` starts with a recent declined suggestion in `suggestion_history` to show suppression

## Quick Test Guidance

### 1) Start PostgreSQL on Docker Compose (port 6433)

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
chmod +x db_persist/14A/manage_postgres.sh
./db_persist/14A/manage_postgres.sh up
```

The compose stack includes:

- `db_persist/14A/docker-compose.yml`
- init SQL: `db_persist/14A/sql/init/001-init.sql` (creates `adk_sessions` and schema `adk_module14a` on first boot)

Common management commands:

```bash
./db_persist/14A/manage_postgres.sh status
./db_persist/14A/manage_postgres.sh create-db
./db_persist/14A/manage_postgres.sh create-schema
./db_persist/14A/manage_postgres.sh reset-schema
./db_persist/14A/manage_postgres.sh reset-db
./db_persist/14A/manage_postgres.sh down
./db_persist/14A/manage_postgres.sh destroy
```

Quick verification:

```sql
SELECT schemaname, tablename
FROM pg_tables
WHERE tablename LIKE 'sessions%' OR tablename LIKE 'events%'
ORDER BY schemaname, tablename;
```

### 2) Ensure dependencies

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m pip install -r requirements.txt
```

### 3) Run CLI use case

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass

# --- Normal coaching runs (builds spending_log over 3+ weeks to trigger trend) ---
./.venv/bin/python -m db_persist.14A.main CUST-3001
./.venv/bin/python -m db_persist.14A.main CUST-3001
./.venv/bin/python -m db_persist.14A.main CUST-3001

# --- Custom simulation snapshot ---
./.venv/bin/python -m db_persist.14A.main CUST-3001 --week 2026-W20 --category travel --amount 777.5

# --- Responding to a coaching suggestion ---
# Use --response with: accepted | declined | not_now
./.venv/bin/python -m db_persist.14A.main CUST-3001 --response accepted
./.venv/bin/python -m db_persist.14A.main CUST-3001 --response declined
./.venv/bin/python -m db_persist.14A.main CUST-3001 --response not_now

# You can also combine with a snapshot in the same call:
./.venv/bin/python -m db_persist.14A.main CUST-3001 --week 2026-W21 --category dining --amount 320 --response accepted

# Legacy: embed the keyword in the prompt string (backward compatible)
./.venv/bin/python -m db_persist.14A.main "CUST-3001 declined"

# Suppression demo (CUST-3003 starts with a declined suggestion 10 days ago)
./.venv/bin/python -m db_persist.14A.main CUST-3003
```

### 4) Start standalone FastAPI

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
chmod +x db_persist/14A/run_14a_api_server.sh db_persist/14A/run_14a_api.sh
./db_persist/14A/run_14a_api_server.sh
```

### 5) Call API with curl helper

Script signature: `./run_14a_api.sh [prompt] [user_id] [session_id] [week] [category] [amount] [response]`

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass

# Basic coaching run
./db_persist/14A/run_14a_api.sh CUST-3001

# With session scope
./db_persist/14A/run_14a_api.sh CUST-3001 api-user-A spending-coach-cust-3001

# With snapshot override
./db_persist/14A/run_14a_api.sh CUST-3001 api-user-A spending-coach-cust-3001 2026-W21 travel 455.25

# Responding to a coaching suggestion (7th arg: accepted | declined | not_now)
./db_persist/14A/run_14a_api.sh CUST-3001 api-user-A "" "" "" "" accepted
./db_persist/14A/run_14a_api.sh CUST-3001 api-user-A "" "" "" "" declined
./db_persist/14A/run_14a_api.sh CUST-3001 api-user-A "" "" "" "" not_now

# Snapshot + response in one call
./db_persist/14A/run_14a_api.sh CUST-3001 api-user-A spending-coach-cust-3001 2026-W21 dining 380 accepted
```

In default `MODULE14A_SESSION_SCOPE=customer` mode all those calls resume the same
persisted customer thread even if caller `user_id` differs.
Set `MODULE14A_SESSION_SCOPE=user` if you want strict caller-user isolation.

Direct curl — coaching run with dedicated `customer_response` field:

```bash
# Normal coaching run with snapshot override
curl -sS http://127.0.0.1:8740/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "CUST-3001",
    "user_id": "curl-user",
    "session_id": "spending-coach-cust-3001",
    "week": "2026-W21",
    "category": "travel",
    "amount": 455.25
  }' | python3 -m json.tool

# Accepting a coaching suggestion
curl -sS http://127.0.0.1:8740/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "CUST-3001",
    "user_id": "curl-user",
    "customer_response": "accepted"
  }' | python3 -m json.tool

# Declining
curl -sS http://127.0.0.1:8740/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "CUST-3001",
    "user_id": "curl-user",
    "customer_response": "declined"
  }' | python3 -m json.tool

# Not now / remind later
curl -sS http://127.0.0.1:8740/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "CUST-3001",
    "user_id": "curl-user",
    "customer_response": "not_now"
  }' | python3 -m json.tool
```

## Code Flow Walkthrough

```mermaid
sequenceDiagram
    participant CLI as CLI/Curl Client
    participant API as FastAPI (db_persist/14A/api_app.py)
    participant Main as Runner (db_persist/14A/main.py)
    participant DB as PostgreSQL:6433
    participant Log as spending_log_agent
    participant Coach as spending_coaching_agent
    participant Tools as 14A tools.py

    CLI->>API: POST /chat (prompt, user_id, session_id?, week?, category?, amount?, customer_response?)
    API->>Main: run_prompt(...)
    Note over Main: derive effective user_id\n(scope=customer => customer::<customer_id>)
    Main->>DB: get_session(app_name, effective_user_id, session_id)
    alt new session
      Main->>DB: create_session(..., seed state)
    end
    Note over Main,DB: DB connect uses search_path=adk_module14a
    Main->>Log: run stage 1
    Log->>Tools: get_weekly_transactions_with_input(customer_id, week?, category?, amount?)
    Log->>Tools: append_spending_snapshot(...)
    Tools->>DB: ADK persists updated session.state
    Main->>Coach: run stage 2
    Coach->>Tools: check_trend_and_suppression(customer_id)
    opt customer response provided
      Coach->>Tools: record_suggestion_response(...)
      Tools->>DB: ADK persists suggestion_history
    end
    Main-->>API: final markdown response
    API-->>CLI: JSON envelope (response + session_id)
```
