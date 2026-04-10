# Module 11: MCP Server (OpenAPI artifacts)

This folder implements **Module 11** as a generic MCP server that loads OpenAPI specs from a folder, indexes operations by `operationId`, and exposes search and mock-generation tools to ADK agents or any other MCP-compatible client.

## Files

- `server.py`
  - Builds the FastMCP server.
  - Supports `stdio` and `streamable-http`.
  - Exposes tools for spec listing, operation search, full operation details, and mock payload generation.
- `openapi_loader.py`
  - Loads `.json`, `.yaml`, and `.yml` specs from a configured folder.
  - Resolves internal `$ref` pointers and builds an operation-centric in-memory index at startup.
- `mock_payloads.py`
  - Generates deterministic request and response examples from resolved schemas.
- `agent.py`
  - Builds the Module 11 ADK `LlmAgent`.
  - Connects to the MCP server over `stdio` by default, or `streamable-http` when configured.
- `main.py`
  - Exposes `run_prompt(...)` and async `stream_prompt(...)`.
  - Matches the API/React chat registration contract used by the rest of the repo.
- `specs/`
  - Default folder scanned at startup when `MODULE11_SPECS_DIR` is not set.
  - Includes a small demo banking spec so Module 11 works immediately.

## Environment variables

Set these in `.env` (or shell):

```dotenv
# OpenAPI source folder
MODULE11_SPECS_DIR=

# ADK-side transport for the chat-selectable Module 11 agent
MODULE11_MCP_TRANSPORT=stdio
MODULE11_MCP_TIMEOUT=20

# Optional stdio override. By default the agent launches:
#   <sys.executable> -m mcp_server.server --transport stdio [--specs-dir ...]
MODULE11_MCP_COMMAND=
MODULE11_MCP_ARGS=

# Remote streamable HTTP mode (used when MODULE11_MCP_TRANSPORT=streamable-http)
MODULE11_MCP_HTTP_URL=http://127.0.0.1:8765/mcp
MODULE11_MCP_HTTP_READ_TIMEOUT=300
# MODULE11_MCP_HTTP_HEADERS_JSON={"Authorization":"Bearer demo-token"}

# Server-side defaults for running the MCP server directly
MODULE11_SERVER_TRANSPORT=stdio
MODULE11_MCP_HOST=127.0.0.1
MODULE11_MCP_PORT=8765
MODULE11_MCP_HTTP_PATH=/mcp
```

## Run directly (CLI)

### 1. Use the Module 11 ADK agent

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m mcp_server.main \
  "Find the customer profile operation and generate a mock response."
```

### 2. Run the MCP server over stdio

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m mcp_server.server --transport stdio --print-config
```

### 3. Run the MCP server over streamable HTTP

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m mcp_server.server \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8765 \
  --http-path /mcp
```

## Tool ideas

- `list_specs` to see what was loaded at startup
- `search_operations` to find operation ids from business language
- `get_operation_details` to inspect full request/response schema
- `generate_mock_request` for example request payloads
- `generate_mock_response` for example response bodies by status code

## Chat UI wiring

This module is wired through:

- `agents.json` entry with `"key": "mcp_server"` and `"module": "mcp_server.main"`
- `"supports_streaming": true` so React uses `POST /api/chat/stream`

Once API + UI are running, select **MCP Server (OpenAPI explorer)** in the agent list.
