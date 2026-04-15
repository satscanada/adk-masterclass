# Module 14A Guide

Module 14A implements a persistent spending-pattern coach using ADK `DatabaseSessionService` with PostgreSQL.

## Use Case

- Input customer IDs: `CUST-3001`, `CUST-3002`, `CUST-3003`
- Stage 1 (`spending_log_agent`) appends a weekly spend snapshot to `session.state["spending_log"]`
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
./.venv/bin/python -m db_persist.14A.main CUST-3001
./.venv/bin/python -m db_persist.14A.main CUST-3001
./.venv/bin/python -m db_persist.14A.main CUST-3001
./.venv/bin/python -m db_persist.14A.main CUST-3003
```

### 4) Start standalone FastAPI

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
chmod +x db_persist/14A/run_14a_api_server.sh db_persist/14A/run_14a_api.sh
./db_persist/14A/run_14a_api_server.sh
```

### 5) Call API with curl helper

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./db_persist/14A/run_14a_api.sh CUST-3001
./db_persist/14A/run_14a_api.sh CUST-3001 api-user-A spending-coach-cust-3001
./db_persist/14A/run_14a_api.sh "CUST-3001 declined" api-user-B spending-coach-cust-3001
```

In default `MODULE14A_SESSION_SCOPE=customer` mode, those last two calls still resume
the same persisted customer thread even though the caller `user_id` differs.
Set `MODULE14A_SESSION_SCOPE=user` if you want strict caller-user isolation instead.

Direct curl:

```bash
curl -sS http://127.0.0.1:8740/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "CUST-3001",
    "user_id": "curl-user",
    "session_id": "spending-coach-cust-3001"
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

    CLI->>API: POST /chat (prompt, user_id, session_id?)
    API->>Main: run_prompt(...)
    Note over Main: derive effective user_id\n(scope=customer => customer::<customer_id>)
    Main->>DB: get_session(app_name, effective_user_id, session_id)
    alt new session
      Main->>DB: create_session(..., seed state)
    end
    Note over Main,DB: DB connect uses search_path=adk_module14a
    Main->>Log: run stage 1
    Log->>Tools: get_weekly_transactions(customer_id)
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
