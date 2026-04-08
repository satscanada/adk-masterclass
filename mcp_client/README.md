# Module 10: MCP Client (Redis business banking)

This folder implements the **Module 10** lesson as an ADK MCP client that connects to a Redis MCP server and uses Redis as working memory for a business banking assistant.

## Files

- `agent.py`
  - Creates `module10_mcp_redis_banking_agent` (`LlmAgent`).
  - Attaches `McpToolset` with `StdioConnectionParams`.
  - Reads MCP process settings from env vars.
- `main.py`
  - Exposes `run_prompt(...)` and async `stream_prompt(...)`.
  - Matches the API/React chat registration contract from `agent_registry.py`.
- `__init__.py`
  - Marks this folder as a package.

## Environment variables

Set these in `.env` (or shell):

```dotenv
# MCP stdio process command + args for the Redis MCP server
MODULE10_MCP_COMMAND=uvx
MODULE10_MCP_ARGS=--from redis-mcp-server@latest redis-mcp-server

# Optional: MCP session timeout (seconds)
MODULE10_MCP_TIMEOUT=20

# Redis connection that Module 10 passes to MCP as an argument
# Preferred:
MODULE10_REDIS_URL=redis://127.0.0.1:6379/0
#
# Or separate fields (used when MODULE10_REDIS_URL is empty):
MODULE10_REDIS_HOST=127.0.0.1
MODULE10_REDIS_PORT=6379
MODULE10_REDIS_DB=0
# MODULE10_REDIS_USERNAME=
# MODULE10_REDIS_PASSWORD=
```

The agent composes a Redis URL from `.env` values and appends `--url <redis://...>` when no explicit connection args are present, matching the official Redis MCP server usage (`uvx --from redis-mcp-server@latest redis-mcp-server --url redis://host:port/db`).

## Run directly (CLI)

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m mcp_client.main \
  "CUST-1002: evaluate cash-flow risk, save summary + next action in Redis memory."
```

## Business banking prompt ideas

- `CUST-1001: summarize profile and store in Redis`
- `CUST-1001: retrieve prior Redis summary and update next action`
- `CUST-2002: recommend overdraft coaching plan and persist memory`

## Chat UI wiring

This module is wired through:

- `agents.json` entry with `"key": "mcp_client"` and `"module": "mcp_client.main"`
- `"supports_streaming": true` so React uses `POST /api/chat/stream`

Once API + UI are running, select **MCP Client (Redis banking)** in the agent list.
