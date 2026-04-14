# CODEFLOW

This document explains the codebase for someone who is new to Python and new to Google ADK.

The goal is to help you answer three questions:

1. What does each file do?
2. What happens when I run the app?
3. What Python syntax is being used here?

## Big Picture

This project now has 20 main parts:

- `simple_litellm_agent/`: the actual ADK agent code
- `mulit_agent/`: a simple Module 02 example with two independent agents
- `orchestrate_agent/`: a simple Module 03 example with deterministic routing to 3 specialists
- `streaming_agent/`: Module 04 — `Runner.run_async()` chunks surfaced to the React UI via NDJSON
- `advanced_agent/`: Module 05 — weather-only LLM agent with Meteosource + temperature tools
- `custom_agent/`: Module 06 — `BaseAgent` keyword router delegating to two `LlmAgent` children
- `multi_agent_banking/`: Module 07 — `SequentialAgent` pipeline for business banking overdraft approval (deposit, bill, and decision agents)
- `workflow_agent/`: Module 08 — workflow orchestrators for retail deposit operations (`LoopAgent`, `ParallelAgent`, and composition)
- `function_tools_agent/`: Module 09 — function tools, long-running tool flow, and agent-as-a-tool composition
- `mcp_client/`: Module 10 — MCP client lesson using Redis MCP server tools for business banking memory
- `mcp_server/`: Module 11 — custom MCP server lesson that loads OpenAPI specs, searches operations, and generates mock payloads
- `retail_deposit_api_agent/`: Module 26 — sequential retail deposit workflow (intake → risk → decision) returning JSON for API clients
- `agents.json`: the list of agents shown in the UI
- `agent_registry.py`: a small registry that lists available agents
- `api_app.py`: the shared HTTP API for external clients
- `streamlit_app.py`: the original chat UI
- `ui/`: the React + Vite + Tailwind chat UI
- `run_banking.sh`: optional CLI wrapper for Module 07 (approve / deny / both customers, no API or React)
- `run_workflow.sh`: optional CLI wrapper for Module 08 (workflow scenarios, no API or React)
- `run_function_tools.sh`: optional CLI wrapper for Module 09 (function-tools scenarios, no API or React)
- `retail_deposit_api_agent/run_retail_deposit_api.sh`: optional curl wrapper for Module 26 standalone API (`POST /chat`)

There are also `tests/agent_registry_smoke_test.py`, `tests/smoke_test.py`, `tests/mulit_agent_smoke_test.py`, `tests/orchestrate_agent_smoke_test.py`, `tests/multi_agent_banking_smoke_test.py`, `tests/mcp_server_loader_smoke_test.py`, `tests/mcp_server_mock_payload_test.py`, and `tests/api_smoke_test.py`, which check that the registry, agents, OpenAPI tooling, and API work correctly.

## Read The Project In This Order

If you are a beginner, read the files in this order:

1. `README.md`
2. `simple_litellm_agent/config.py`
3. `simple_litellm_agent/agent.py`
4. `simple_litellm_agent/main.py`
5. `mulit_agent/agent.py`
6. `mulit_agent/main.py`
7. `orchestrate_agent/agent.py`
8. `orchestrate_agent/main.py`
9. `streaming_agent/agent.py`
10. `streaming_agent/main.py`
11. `advanced_agent/weather_tools.py`
12. `advanced_agent/agent.py`
13. `advanced_agent/main.py`
14. `custom_agent/agent.py`
15. `custom_agent/main.py`
16. `multi_agent_banking/banking_tools.py`
17. `multi_agent_banking/agent.py`
18. `multi_agent_banking/main.py`
19. `workflow_agent/workflow_tools.py`
20. `workflow_agent/agent.py`
21. `workflow_agent/main.py`
22. `function_tools_agent/function_tools.py`
23. `function_tools_agent/agent.py`
24. `function_tools_agent/main.py`
25. `mcp_client/agent.py`
26. `mcp_client/main.py`
27. `mcp_server/openapi_loader.py`
28. `mcp_server/mock_payloads.py`
29. `mcp_server/server.py`
30. `mcp_server/agent.py`
31. `mcp_server/main.py`
32. `agents.json`
33. `agent_registry.py`
34. `api_app.py`
35. `streamlit_app.py`
36. `AGENT_HELP.md` (module reference; keep in sync with `ui/src/help/agentHelp.js`)
37. `ui/src/help/agentHelp.js` and `ui/src/help/HelpOverlay.jsx`
38. `ui/src/App.jsx`
39. `retail_deposit_api_agent/agent.py`
40. `retail_deposit_api_agent/main.py`
41. `retail_deposit_api_agent/run_retail_deposit_api.sh`
42. `tests/agent_registry_smoke_test.py`
43. `tests/smoke_test.py`
44. `tests/mulit_agent_smoke_test.py`
45. `tests/orchestrate_agent_smoke_test.py`
46. `tests/multi_agent_banking_smoke_test.py`
47. `tests/mcp_server_loader_smoke_test.py`
48. `tests/mcp_server_mock_payload_test.py`
49. `tests/api_smoke_test.py`

That order goes from simple configuration to the full app flow.

## Folder Map

```text
adk-masterclass/
├── README.md
├── AGENT_HELP.md
├── CODEFLOW.md
├── requirements.txt
├── run.sh
├── run_banking.sh
├── run_function_tools.sh
├── run_workflow.sh
├── runstreamlit.sh
├── api_app.py
├── agents.json
├── agent_registry.py
├── streamlit_app.py
├── ui/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── help/
│       │   ├── agentHelp.js
│       │   └── HelpOverlay.jsx
│       ├── App.jsx
│       ├── index.css
│       └── main.jsx
├── tests/
│   ├── api_smoke_test.py
│   ├── smoke_test.py
│   ├── mulit_agent_smoke_test.py
│   ├── orchestrate_agent_smoke_test.py
│   ├── multi_agent_banking_smoke_test.py
│   ├── mcp_server_loader_smoke_test.py
│   ├── mcp_server_mock_payload_test.py
│   └── agent_registry_smoke_test.py
├── mulit_agent/
│   ├── __init__.py
│   ├── agent.py
│   └── main.py
├── orchestrate_agent/
│   ├── __init__.py
│   ├── agent.py
│   └── main.py
├── streaming_agent/
│   ├── __init__.py
│   ├── agent.py
│   └── main.py
├── advanced_agent/
│   ├── __init__.py
│   ├── agent.py
│   ├── main.py
│   └── weather_tools.py
├── custom_agent/
│   ├── __init__.py
│   ├── agent.py
│   └── main.py
├── multi_agent_banking/
│   ├── __init__.py
│   ├── agent.py
│   ├── main.py
│   └── banking_tools.py
├── workflow_agent/
│   ├── __init__.py
│   ├── agent.py
│   ├── main.py
│   └── workflow_tools.py
├── function_tools_agent/
│   ├── __init__.py
│   ├── agent.py
│   ├── main.py
│   └── function_tools.py
├── mcp_client/
│   ├── __init__.py
│   ├── agent.py
│   ├── main.py
│   └── README.md
├── mcp_server/
│   ├── __init__.py
│   ├── agent.py
│   ├── main.py
│   ├── mock_payloads.py
│   ├── openapi_loader.py
│   ├── server.py
│   ├── README.md
│   └── specs/
│       └── business_banking_demo.yaml
├── retail_deposit_api_agent/
│   ├── __init__.py
│   ├── agent.py
│   ├── api_app.py
│   ├── README.md
│   ├── run_retail_deposit_api.sh
│   └── main.py
└── simple_litellm_agent/
    ├── __init__.py
    ├── config.py
    ├── agent.py
    └── main.py
```

## What Each File Does

### `requirements.txt`

Lists Python packages this project needs:

- `google-adk`: Google Agent Development Kit
- `litellm`: adapter for OpenAI-compatible model APIs
- `python-dotenv`: loads environment variables from `.env`
- `streamlit`: web UI
- `celery[redis]`: optional Module 09 async task queue demo (Redis broker/backend)
- `mcp`: Model Context Protocol SDK used by Modules 10 and 11
- `PyYAML`: YAML parser for OpenAPI spec loading in Module 11

### `simple_litellm_agent/config.py`

This file reads configuration from environment variables.

It is responsible for:

- loading `.env`
- reading model settings
- building a `Settings` object
- normalizing the API base URL

Think of this file as: "read all the knobs and switches for the app."

### `simple_litellm_agent/agent.py`

This file creates the ADK agent.

It:

- imports `Agent` from Google ADK
- imports `LiteLlm`
- creates the model connection
- returns an ADK `Agent(...)`

Think of this file as: "build the brain."

### `simple_litellm_agent/main.py`

This file runs the agent.

It:

- builds a `Runner`
- creates or reuses sessions
- sends the user's prompt
- reads events from ADK
- extracts the final text reply

Think of this file as: "send a prompt in, get an answer out."

### `mulit_agent/agent.py`

This file creates two ADK agents for the Module 02 lesson.

It:

- builds a writer agent
- builds a bullet-point agent
- gives each agent a simple instruction

Think of this file as: "build two small specialist brains."

### `mulit_agent/main.py`

This file runs both agents for the same topic.

It:

- builds two `Runner` objects
- sends the same chat topic to both agents
- collects both answers
- combines them into one markdown response

Think of this file as: "ask two specialists, then show both answers together."

### `orchestrate_agent/agent.py`

This file creates 3 ADK agents for the Module 03 lesson.

It:

- builds an `explain` agent
- builds a `bullet` agent
- builds a `quiz` agent
- gives each agent a narrow instruction

Think of this file as: "build three small specialists for deterministic routing."

### `orchestrate_agent/main.py`

This file runs the deterministic orchestrator.

It:

- reads the `agent_type` line from the prompt
- validates that the type is one of `explain`, `bullet`, or `quiz`
- strips the routing line from the user's request
- forwards a routed prompt that includes `Agent type intent: ...`
- runs only the matching specialist

Think of this file as: "read the route, pick one specialist, then run only that one."

### `streaming_agent/agent.py`

This file creates one ADK agent for the Module 04 lesson.

It:

- names the agent `streaming_agent`
- sets an instruction that asks for multiple sentences
- uses the same LiteLLM settings as `simple_litellm_agent`, with a higher minimum token budget

Think of this file as: "one model, ready to stream events."

### `streaming_agent/main.py`

This file runs the streaming agent two ways.

It:

- builds a `Runner` with `auto_create_session=True`
- implements `run_prompt(...)` using the synchronous `runner.run(...)` path (same idea as Module 01, for Streamlit and blocking HTTP)
- implements async `stream_prompt(...)` that loops `async for event in runner.run_async(...)` and yields text from assistant content parts
- includes a small `__main__` demo that prints chunks with `flush=True`

Think of this file as: "Module 04 — stream in async mode, or buffer the full answer in sync mode."

### `advanced_agent/weather_tools.py`

This file defines two plain Python functions used as ADK tools for Module 05.

It:

- reads `WEATHER_API_KEY` from the environment
- implements `fetch_current_weather(place_id)` against the Meteosource free `point` endpoint (`units=metric` so temperature is Celsius)
- implements `celsius_to_fahrenheit_display(celsius)` for paired °C / °F output

Think of this file as: "real HTTP tool + small conversion helper."

### `advanced_agent/agent.py`

This file builds the Module 05 `Agent`.

It:

- attaches `fetch_current_weather` and `celsius_to_fahrenheit_display` to `tools=[...]`
- sets `output_key` so the final reply is stored on session state
- uses strict instructions: weather-only scope, otherwise a single fixed refusal sentence

Think of this file as: "tool-using LLM agent with a narrow domain."

### `advanced_agent/main.py`

This file runs the weather assistant with both blocking and streaming paths.

It:

- caches a `Runner` for the process
- exposes `run_prompt(...)` for Streamlit, `POST /api/chat`, and CLI
- exposes async `stream_prompt(...)` that loops `runner.run_async(...)` and yields text chunks for `POST /api/chat/stream` (same pattern as Module 04)
- exposes `reset_runtime()` for tests that swap environment variables

Think of this file as: "tool-using agent with sync or streamed assistant tokens."

### `custom_agent/agent.py`

This file defines the Module 06 custom `BaseAgent` subclass.

It:

- declares two `LlmAgent` children as Pydantic fields (`tech_agent`, `general_agent`)
- implements `_run_async_impl` to read user text from `InvocationContext.user_content`
- picks tech vs general using a small keyword set (no LLM router)
- delegates by iterating `chosen.run_async(ctx)` and re-yielding events (same pattern as ADK’s `SequentialAgent`)

Think of this file as: "rule-based router + LLM specialists."

### `custom_agent/main.py`

This file runs the custom agent with both blocking and streaming paths.

It:

- caches a `Runner` for the process
- exposes `run_prompt(...)` for Streamlit, `POST /api/chat`, and CLI
- exposes async `stream_prompt(...)` for `POST /api/chat/stream` (NDJSON in the React UI)
- exposes `reset_runtime()` for tests that swap environment variables

Think of this file as: "BaseAgent tree with the same streaming contract as Module 04."

### `multi_agent_banking/banking_tools.py`

This file defines mock banking data and five tool functions for Module 07.

It:

- stores two demo customers in a `_CUSTOMER_DB` dictionary (`CUST-1001` Acme Corp, `CUST-2002` Sunrise Bakery)
- implements `get_monthly_deposits(customer_id)` — returns deposit transactions and totals
- implements `get_balance_movement(customer_id)` — returns daily balance snapshots, min/max/avg
- implements `get_completed_bills(customer_id)` — returns bills paid in the last month
- implements `get_upcoming_bills(customer_id)` — returns scheduled bills for the next month
- implements `get_overdraft_request(customer_id)` — returns the customer's account details, requested overdraft limit, and **`demo_expected_decision`** (`APPROVE` for `CUST-1001`, `DENY` for `CUST-2002`) so the teaching scenario stays consistent

Think of this file as: "the mock bank database and API."

### `multi_agent_banking/agent.py`

This file builds the Module 07 `SequentialAgent` pipeline.

It:

- creates `deposit_agent` with tools `get_monthly_deposits` and `get_balance_movement`, writing to `output_key="deposit_analysis"`
- creates `bill_agent` with tools `get_completed_bills` and `get_upcoming_bills`, writing to `output_key="bill_analysis"`
- creates `decision_agent` with tool `get_overdraft_request`, reading `{deposit_analysis}` and `{bill_analysis}` from session state; instructions require the final **Decision** line to match `demo_expected_decision` from the tool
- wraps all three in a `SequentialAgent` named `banking_overdraft_pipeline`
- deposit and bill agents instruct the model to **call both tools** before writing analysis (reduces skipped-tool runs)

Think of this file as: "three specialist brains wired in a pipeline."

### `multi_agent_banking/main.py`

This file runs the banking pipeline with both blocking and streaming paths.

It:

- caches a `Runner` for the process
- exposes `run_prompt(...)` for Streamlit, `POST /api/chat`, and CLI
- exposes async `stream_prompt(...)` that yields text chunks from each pipeline stage for `POST /api/chat/stream`
- prepends a pipeline banner showing the agent sequence
- emits **audit trail events** — sentinel-prefixed strings (`\x00AUDIT:{json}`) for agent transitions, tool calls, and tool results. `api_app.py` detects these sentinels and converts them to `{"type":"audit",...}` NDJSON events, which the React UI renders as a live-updating pipeline timeline
- resolves the owning agent per event with **`_effective_agent_name()`** (uses `event.branch` leaf when `author` is missing or `user`) and a **`_TOOL_TO_AGENT`** map so tool rows still attribute to `deposit_agent` / `bill_agent` / `decision_agent` when the stream omits metadata
- skips events with no `content.parts` **before** agent transitions so empty shell events do not steal `current_agent`

Think of this file as: "Module 07 — three agents in sequence, streamed or buffered, with full observability."

### `workflow_agent/workflow_tools.py`

This file defines mock data and tool functions for Module 08 (retail deposit workflows).

It:

- stores two demo retail customers (`RET-3101` healthy, `RET-4420` higher-risk)
- implements profile and deposit retrieval tools (`get_deposit_profile`, `get_recent_deposits`)
- implements risk checks (`run_aml_screening`, `run_velocity_check`)
- implements loop tooling for operational reconciliation (`fetch_next_deposit_exception`, `clear_deposit_exception`)
- exposes `get_deposit_offer_request` with deterministic `demo_expected_offer`
- includes `reset_workflow_state()` to clear the loop cursor before each CLI run

Think of this file as: "mock retail core-banking deposit tools + loop state."

### `workflow_agent/agent.py`

This file builds the Module 08 workflow-agent scenarios.

It:

- creates a `LoopAgent` (`deposit_exception_loop`) where one resolver agent processes one pending exception per iteration
- creates a `ParallelAgent` (`deposit_parallel_assessment`) that runs deposit-health and compliance-risk analyses concurrently
- creates a composition pattern with `SequentialAgent(ParallelAgent -> LoopAgent -> final_offer_agent)`
- forces deterministic final recommendation in the composition step by matching tool field `demo_expected_offer`

Think of this file as: "workflow orchestration patterns over one deposit use case."

### `workflow_agent/main.py`

This file runs Module 08 from the CLI (no API/UI integration).

It:

- accepts `--scenario` as `loop`, `parallel`, or `composition`
- caches one `Runner` per scenario with `InMemorySessionService`
- resets loop cursor state before execution so exception replay always starts at item 1
- prints a **terminal audit trail** by default (agent start/end, tool calls with JSON args, tool results with summaries); use `--quiet` for final text only
- normalizes customer aliases in Python (`week` -> `RET-4420`, same as `run_workflow.sh`)
- reuses the same `run_prompt(...)` contract but keeps this module intentionally outside `agents.json`

Think of this file as: "scenario-driven CLI runner for Module 08 workflow lessons."

### `function_tools_agent/function_tools.py`

This file defines Module 09 function tools.

It:

- reuses Module 08 retail tools and Module 07 business tools for real examples
- provides basic snapshot functions suitable for `tools=[...]`
- provides a long-running starter function (`ask_for_exception_clearance`) returning pending + ticket ID
- provides a completion function (`apply_exception_clearance`) for the resumed turn
- includes reset helper state for repeatable demos

Think of this file as: "custom function tools with banking-domain outputs."

### `function_tools_agent/agent.py`

This file builds three Module 09 agent patterns.

It:

- creates a basic-tools `LlmAgent` using plain Python functions
- creates a long-running `LlmAgent` using `LongRunningFunctionTool`
- creates an agent-as-a-tool root `LlmAgent` using `AgentTool(...)`
- creates a Celery-backed async banking `LlmAgent` for queued recalculation tasks

Think of this file as: "FunctionTool + LongRunningFunctionTool + AgentTool in one lesson."

### `function_tools_agent/main.py`

This file runs Module 09 from the CLI.

It:

- supports scenarios `basic`, `long-running`, `agent-as-tool`, and `celery`
- demonstrates long-running flow in two turns (pending first turn, approval `FunctionResponse` second turn)
- prints one final markdown result for terminal learning

Think of this file as: "CLI harness for all Module 09 tool patterns."

### `mcp_client/agent.py`

This file builds the Module 10 MCP client agent.

It:

- creates one `LlmAgent` for business banking advisory
- attaches `McpToolset` with `StdioConnectionParams` to connect to a Redis MCP server process
- reads MCP command/args/timeout from `MODULE10_MCP_COMMAND`, `MODULE10_MCP_ARGS`, and `MODULE10_MCP_TIMEOUT`
- instructs the model to use customer-scoped Redis key prefixes for memory (`banking:customer:{id}:...`)

Think of this file as: "ADK agent + MCP bridge to Redis tools."

### `mcp_client/main.py`

This file runs Module 10 with both blocking and streaming paths.

It:

- caches a `Runner` for the process
- exposes `run_prompt(...)` for `POST /api/chat` and CLI
- exposes async `stream_prompt(...)` for `POST /api/chat/stream`
- raises actionable setup errors when Redis MCP command/args are not available

Think of this file as: "MCP client lesson runner that is UI-ready."

### `mcp_server/openapi_loader.py`

This file loads and normalizes Module 11 OpenAPI specs.

It:

- scans a configured folder for `.json`, `.yaml`, and `.yml` files
- parses OpenAPI documents and walks `paths`
- resolves internal `$ref` pointers
- builds an operation-centric index keyed by `operationId` (with a synthetic fallback when missing)

Think of this file as: "startup OpenAPI parser + searchable operation index."

### `mcp_server/mock_payloads.py`

This file generates deterministic examples from resolved schemas.

It:

- prefers `example`, `default`, `enum`, and `const` values when present
- handles nested objects, arrays, and primitive types
- builds mock request and response payloads for Module 11 tools

Think of this file as: "schema-to-example payload generator."

### `mcp_server/server.py`

This file builds the Module 11 MCP server.

It:

- creates a `FastMCP` server
- loads the OpenAPI index at startup
- exposes tools for spec listing, operation search, full operation details, and mock generation
- runs over `stdio` or `streamable-http`

Think of this file as: "custom MCP server over your OpenAPI artifacts."

### `mcp_server/agent.py`

This file builds the Module 11 MCP client agent.

It:

- creates one `LlmAgent` for API integration assistance
- attaches `McpToolset` with either `StdioConnectionParams` or `StreamableHTTPConnectionParams`
- defaults to spawning the local `mcp_server.server` module over stdio
- can point to a remote streamable HTTP MCP server via env vars

Think of this file as: "ADK client for your own MCP server."

### `mcp_server/main.py`

This file runs Module 11 with both blocking and streaming paths.

It:

- caches a `Runner` for the process
- exposes `run_prompt(...)` for `POST /api/chat` and CLI
- exposes async `stream_prompt(...)` for `POST /api/chat/stream`
- raises actionable setup errors when Module 11 MCP transport configuration is invalid

Think of this file as: "OpenAPI MCP lesson runner that is UI-ready."

### `retail_deposit_api_agent/agent.py`

This file builds the Module 26 `SequentialAgent` API workflow.

It:

- creates `deposit_intake_agent` (profile + recent deposit tools)
- creates `deposit_risk_agent` (AML + velocity tools)
- creates `deposit_decision_agent` (offer lookup + strict JSON contract output)
- chains all three in one `SequentialAgent`

Think of this file as: "multi-step retail deposit pipeline that ends in JSON."

### `retail_deposit_api_agent/main.py`

This file runs Module 26 with a blocking API-friendly contract.

It:

- caches one `Runner` per process
- exposes `run_prompt(...)` for `POST /api/chat` and CLI use
- extracts and validates a final JSON object from the model output
- returns normalized pretty JSON text for reliable client parsing

Think of this file as: "JSON-first runner for the sequential retail workflow."

### `agents.json`

This file stores the list of agents for the app.

Each agent entry contains:

- `key`
- `title`
- `description`
- `prompt_hint`
- `module`
- optional `supports_streaming` (when `true`, the Python module must define `stream_prompt`)
- optional **`suggestions`** — array of `{ "label", "prompt" }` objects; the React UI shows **Quick start** chips when the conversation is empty (Module 07 uses this for the two demo customers)

Think of this file as: "the data that describes the menu."

### `agent_registry.py`

This file keeps a list of chat agents for the UI.

It now loads agent metadata from `agents.json` and uses one shared pattern to import a module and call `run_prompt(...)`.

When `supports_streaming` is true, it also imports `stream_prompt` from the same module and stores it for the API streaming route.

It also passes `prompt_hint` through to the UIs and API, which is helpful for agents like the Module 03 orchestrator that need a fixed prompt format.

Think of this file as: "the menu of available agents."

### `api_app.py`

This file exposes the learning agents over HTTP.

It:

- adds `GET /health`
- adds `GET /api/agents`
- adds `POST /api/chat`
- adds `POST /api/chat/stream` for NDJSON streaming when the registry exposes a stream function — it detects audit sentinel strings and emits them as `{"type":"audit",...}` NDJSON events alongside the regular `{"type":"delta",...}` text chunks
- converts HTTP JSON into the existing `ChatRequest` shape

Think of this file as: "the backend door into the agents."

### `run.sh`

This script starts the FastAPI server and the Vite dev server together for local development.

It frees stale listeners on ports **8512** and **8513**, then runs uvicorn and `npm run dev` in the background and waits until you stop the process.

Think of this file as: "one command to run the main API + React stack."

### `run_banking.sh`

This script runs the Module 07 banking overdraft pipeline from the command line (no UI required).

It:

- accepts `approve` (CUST-1001), `deny` (CUST-2002), `both`, or a custom customer ID
- prints the full pipeline output including the audit trail (agent transitions, tool calls, tool results)
- uses color-coded headers and separators for readability
- normalizes the first argument with **`tr '[:upper:]' '[:lower:]'`** (works on macOS Bash 3.2; avoids `${var,,}` which requires Bash 4+)

Think of this file as: "CLI shortcut for the banking approve / deny scenarios."

### `run_workflow.sh`

This script runs Module 08 workflow scenarios for retail deposit operations.

It:

- clears the terminal at startup (`clear`, with an ANSI escape fallback)
- accepts `loop`, `parallel`, `composition`, or `all`
- accepts customer aliases (`strong` / `healthy` -> `RET-3101`, `weak` / `risk` / `week` -> `RET-4420`)
- executes `python -m workflow_agent.main <customer> --scenario <name>`
- keeps this lesson independent from API and UI agent registration

Think of this file as: "CLI harness for LoopAgent, ParallelAgent, and composition demos."

### `run_function_tools.sh`

This script runs Module 09 examples.

It:

- clears terminal output before runs
- supports `basic`, `long-running`, `agent-as-tool`, `celery`, or `all`
- runs `python -m function_tools_agent.main` with chosen scenario

Think of this file as: "single command entrypoint for Module 09 demos."

### `retail_deposit_api_agent/api_app.py`

This file exposes Module 26 as a standalone FastAPI service.

It:

- adds `GET /health`
- adds `POST /chat` for customer-ID prompts
- calls local `run_prompt(...)` directly (no registry dependency)

Think of this file as: "module-scoped API app for independent runs."

### `retail_deposit_api_agent/run_retail_deposit_api.sh`

This script calls Module 26 standalone API directly.

It:

- sends `POST /chat` using `curl`
- accepts customer ID as the first argument (`RET-3101` default)

Think of this file as: "quick API contract check for Module 26."

### `runstreamlit.sh`

This script starts the optional Streamlit UI.

It frees port **8511** if needed, then runs `streamlit run streamlit_app.py` with the same port and options as before.

Think of this file as: "optional Python-only UI, separate from `run.sh`."

### `tests/agent_registry_smoke_test.py`

This file is a tiny test for the registry itself.

It:

- loads the agent list from `agents.json`
- checks that the registry exposes the same agents
- checks that prompt hints are loaded
- confirms unknown keys raise an error

Think of this file as: "prove the menu loads correctly."

### `streamlit_app.py`

This is the web chat app.

It:

- shows a sidebar with available agents
- shows a prompt hint for the selected agent
- keeps chat history
- creates a session ID
- sends the user's message to the selected agent
- displays the answer

Think of this file as: "the screen the user interacts with."

### `AGENT_HELP.md`

This file is the human-readable **agent module reference**.

It:

- summarizes how `agents.json`, the registry, and the API connect
- compares each learning module in a table
- explains how to add a new agent and keep docs in sync

Think of this file as: "the printable help doc that mirrors the in-app Help panel."

### `ui/src/help/agentHelp.js`

This file holds **structured help data** for the React overlay.

It:

- exports `HELP_META` (titles and intro copy)
- exports `HELP_MODULES` (one object per agent module: key, pattern, API surface)

When you add a new registered agent, append a matching entry here and update `AGENT_HELP.md`.

Think of this file as: "the data behind the Help button."

### `ui/src/help/HelpOverlay.jsx`

This file renders the **Help** modal.

It:

- reads `agentHelp.js`
- shows a **sidebar** (Overview plus one nav item per `HELP_MODULES` entry) and **one detail pane** at a time
- resets to Overview whenever the dialog opens
- locks body scroll while open
- closes on Escape or backdrop click

Think of this file as: "the Help dialog component."

### `ui/src/App.jsx`

This is the React chat app.

It:

- loads the agent list from the Python API
- keeps a separate session ID per selected agent
- sends prompts to `POST /api/chat`, or to `POST /api/chat/stream` when `supports_streaming` is true, and updates the assistant message as each NDJSON `delta` line arrives
- handles `{"type":"audit",...}` events by attaching them to the current assistant message; renders an `AuditTrail` component as a collapsible timeline showing agent transitions, tool calls with **full JSON arguments**, and **JSON output summaries** — grouped by `evt.agent`, updating live during streaming
- shows the returned answer in a chat layout
- opens **Help** (`HelpOverlay`) from the sidebar info button

Think of this file as: "a second front-end that talks to the API instead of importing Python directly."

### `tests/smoke_test.py`

This file is a simple test.

It:

- starts a fake local HTTP server
- points the agent to that server
- runs the prompt
- verifies the request shape

Think of this file as: "prove the wiring works."

### `tests/mulit_agent_smoke_test.py`

This file is a simple test for the multi-agent lesson.

It:

- starts a fake local HTTP server
- runs the multi-agent prompt flow
- confirms there were two model calls
- checks that both calls used the same topic

Think of this file as: "prove both beginner agents are wired correctly."

### `tests/orchestrate_agent_smoke_test.py`

This file is a simple test for the Module 03 orchestrator lesson.

It:

- starts a fake local HTTP server
- runs the orchestrator with `explain`, `bullet`, and `quiz`
- confirms each run includes the correct routed prompt
- checks that missing `agent_type` fails clearly

Think of this file as: "prove deterministic routing works."

### `tests/multi_agent_banking_smoke_test.py`

This file is a smoke test for the Module 07 banking pipeline.

It:

- starts a mock OpenAI-compatible server on port 4015
- runs the full SequentialAgent pipeline for both demo customers (CUST-1001 and CUST-2002)
- validates that the pipeline banner includes all three agent names
- checks that mock tool functions return correct data (deposit counts, balance ranges, bill totals)
- verifies invalid customer IDs return clear error messages

Think of this file as: "prove the multi-agent banking pipeline works end to end."

### `tests/mcp_server_loader_smoke_test.py`

This file is a smoke test for the Module 11 OpenAPI loader.

It:

- creates a temporary OpenAPI spec on disk
- verifies `$ref` resolution for parameters and schemas
- checks operation search behavior
- confirms the synthetic `operationId` fallback for operations that do not define one

Think of this file as: "prove Module 11 can build a searchable startup index from specs."

### `tests/mcp_server_mock_payload_test.py`

This file is a smoke test for the Module 11 mock payload generator.

It:

- loads the bundled demo spec from `mcp_server/specs/`
- builds a mock request for `createOverdraftReview`
- builds mock responses for nested object schemas and headers
- verifies example values survive through the resolved schema path

Think of this file as: "prove Module 11 can turn OpenAPI schemas into useful example payloads."

### `tests/api_smoke_test.py`

This file is a simple test for the FastAPI layer.

It:

- starts a fake local HTTP server
- calls the API routes with `TestClient`
- confirms the API can list agents
- confirms `/api/chat` still reaches the underlying model endpoint
- checks that the streaming agent advertises `supports_streaming: true` in the agent list

Think of this file as: "prove the HTTP wrapper works."

## End-To-End Code Flow

There are 7 useful ways to run this project.

### Flow 1: Run the agent from the command line

Command:

```bash
./.venv/bin/python -m simple_litellm_agent.main
```

What happens:

1. Python starts `simple_litellm_agent/main.py`.
2. `main()` reads the command-line argument.
3. `run_prompt()` is called.
4. `build_runner()` gets settings from `config.py`.
5. `create_agent()` builds the ADK agent from `agent.py`.
6. `Runner(...)` sends your message through ADK.
7. The LiteLLM model adapter sends an HTTP request to your configured API.
8. ADK returns events.
9. `extract_final_text()` pulls out the final assistant message.
10. The text is printed to the terminal.

Short version:

```text
terminal -> main.py -> config.py -> agent.py -> ADK Runner -> LiteLLM API -> final text
```

### Flow 2: Run the Streamlit UI

Command:

```bash
./runstreamlit.sh
```

What happens:

1. The script frees port **8511** if a previous Streamlit is still listening.
2. Streamlit runs `streamlit_app.py`.
3. The app asks `agent_registry.py` for available agents.
4. You choose an agent in the sidebar.
5. You type a prompt in the chat box.
6. The app builds a `ChatRequest`.
7. The selected agent's `run(...)` function is called.
8. The registry imports the module from `agents.json` and calls its `run_prompt(...)` function.
9. The rest of the flow is the same as the command-line version.
10. The answer is shown in the browser.

Short version:

```text
browser -> streamlit_app.py -> agent_registry.py -> run_prompt() -> ADK Runner -> model API
```

### Flow 3: Run the API

Command:

```bash
./.venv/bin/python -m uvicorn api_app:app --host 127.0.0.1 --port 8512 --reload
```

What happens:

1. Uvicorn starts `api_app.py` (default port **8512** in this project).
2. FastAPI exposes `GET /api/agents`, `POST /api/chat`, and `POST /api/chat/stream`.
3. A client sends JSON with `agent_key`, `prompt`, and optional session data.
4. `api_app.py` looks up the selected agent from `agent_registry.py`.
5. For `/api/chat`, the registry imports the configured module and calls `run_prompt(...)`. For `/api/chat/stream`, it calls async `stream_prompt(...)` and streams NDJSON lines.
6. The underlying ADK runner sends the prompt to the model API.
7. FastAPI returns a JSON response with the final text, or a streaming body for NDJSON.

Short version:

```text
client -> api_app.py -> agent_registry.py -> run_prompt() or stream_prompt() -> ADK Runner -> model API -> JSON or NDJSON
```

### Flow 4: Run the React UI

Command:

```bash
cd ui && npm run dev
```

What happens:

1. Vite runs the React app from `ui/` on **port 8513** (see `ui/vite.config.js`).
2. The browser loads `ui/src/App.jsx`.
3. React fetches `GET /api/agents`.
4. You choose an agent and type a prompt.
5. React sends `POST /api/chat` or `POST /api/chat/stream` depending on `supports_streaming`.
6. The Python API runs the selected agent and returns JSON or a chunked NDJSON stream.
7. React appends the answer to the chat history (incrementally when streaming).

Short version:

```text
browser -> React UI -> /api/chat or /api/chat/stream -> api_app.py -> agent_registry.py -> run_prompt() / stream_prompt() -> model API
```

**Tip:** From the repo root, `./run.sh` starts the API (**8512**) and the React dev server (**8513**) together (it does not start Streamlit).

### Flow 5: Run the Module 03 orchestrator

Command:

```bash
./.venv/bin/python -m orchestrate_agent.main $'agent_type: explain\nrequest: Explain what an agent orchestrator does.'
```

What happens:

1. Python starts `orchestrate_agent/main.py`.
2. `run_prompt()` reads the `agent_type` line.
3. The code validates the route deterministically.
4. The remaining text becomes the user request.
5. The orchestrator builds a routed prompt with `Agent type intent: ...`.
6. Only the matching specialist runner is called.
7. ADK sends one model request and returns the final text.

Short version:

```text
terminal -> orchestrate_agent/main.py -> agent_type parser -> chosen Runner -> LiteLLM API -> final text
```

### Flow 6: Run the smoke test

Command:

```bash
./.venv/bin/python tests/smoke_test.py
```

What happens:

1. A fake HTTP server starts on `127.0.0.1:4012`.
2. Environment variables are set to point the agent at that fake server.
3. `run_prompt()` is called.
4. The agent sends a request to the fake server.
5. The fake server replies with `"ok"`.
6. The test checks:
   - the path was `/v1/chat/completions`
   - the bearer token was included
   - the model name was correct
   - the prompt was included

This is a good beginner example because it shows how to test integration without needing a real external service.

### Flow 7: Run the business banking pipeline (Module 07)

Command:

```bash
./.venv/bin/python -m multi_agent_banking.main CUST-1001
# Or: ./run_banking.sh approve   # CUST-1001 only
#     ./run_banking.sh deny      # CUST-2002 only
#     ./run_banking.sh           # both
```

What happens:

1. Python starts `multi_agent_banking/main.py`.
2. `build_runner()` creates a `Runner` wrapping the `SequentialAgent` pipeline.
3. The pipeline sends the customer ID to `deposit_agent` first.
4. `deposit_agent` calls `get_monthly_deposits` and `get_balance_movement` from `banking_tools.py`, then writes its analysis to `session.state["deposit_analysis"]`.
5. Next, `bill_agent` runs with the same session; it calls `get_completed_bills` and `get_upcoming_bills`, then writes to `session.state["bill_analysis"]`.
6. Finally, `decision_agent` runs; it calls `get_overdraft_request`, reads `{deposit_analysis}` and `{bill_analysis}` from state, and produces an overdraft decision.
7. `stream_prompt()` yields each agent's output as it arrives (NDJSON for the React UI), along with audit trail events for agent transitions, tool calls, and tool results. `run_prompt()` collects all three and returns the combined result. The React UI renders audit events as a live-updating pipeline timeline above the assistant response.

Short version:

```text
terminal -> main.py -> SequentialAgent(deposit_agent -> bill_agent -> decision_agent) -> mock tools -> session.state chaining -> combined result
```

### Flow 8: Run the banking approve / deny script

Command:

```bash
./run_banking.sh              # runs both customers
./run_banking.sh approve      # only CUST-1001 (healthy → APPROVE)
./run_banking.sh deny         # only CUST-2002 (weaker  → DENY)
```

What happens:

1. The script resolves the argument to one or both customer IDs.
2. For each customer, it runs `./.venv/bin/python -m multi_agent_banking.main <ID>`.
3. `stream_prompt()` sends the customer ID through the SequentialAgent pipeline.
4. The terminal prints audit events (agent transitions, tool calls and returns) alongside the streamed text output.
5. Color-coded headers make it easy to distinguish the two scenarios when running `both`.

Short version:

```text
run_banking.sh -> multi_agent_banking/main.py -> SequentialAgent -> audit trail + text output
```

### Flow 9: Run a Module 08 workflow scenario directly

Command:

```bash
./.venv/bin/python -m workflow_agent.main RET-3101 --scenario composition
# Or: --scenario loop
#     --scenario parallel
```

What happens:

1. Python starts `workflow_agent/main.py`.
2. `reset_workflow_state()` clears the loop cursor so exception handling starts from the first pending item.
3. A scenario-specific runner is built:
   - `loop` -> `LoopAgent`
   - `parallel` -> `ParallelAgent`
   - `composition` -> `SequentialAgent(ParallelAgent -> LoopAgent -> final_offer_agent)`
4. The customer ID is sent to the selected workflow agent.
5. For composition, parallel analysis runs first, loop reconciliation runs second, then final offer decision is generated from session state.

Short version:

```text
terminal -> workflow_agent/main.py -> selected workflow agent -> retail deposit tools -> final scenario output
```

### Flow 10: Run the Module 08 workflow CLI script

Command:

```bash
./run_workflow.sh                    # all scenarios for RET-3101
./run_workflow.sh loop weak          # loop scenario for RET-4420
./run_workflow.sh composition strong # composition for RET-3101
```

What happens:

1. The script normalizes scenario and customer alias arguments.
2. It maps aliases to customer IDs (`strong` -> `RET-3101`, `weak` / `week` -> `RET-4420`).
3. It runs one or all scenarios by invoking `python -m workflow_agent.main`.
4. Each run prints a scenario header plus final model output in the terminal.

Short version:

```text
run_workflow.sh -> workflow_agent/main.py -> Loop/Parallel/Composition workflow agents -> text output
```

### Flow 11: Run Module 09 function tools directly

Command:

```bash
./.venv/bin/python -m function_tools_agent.main --scenario basic RET-3101
./.venv/bin/python -m function_tools_agent.main --scenario long-running \
  "Request manual approval for RET-4420 due to source-of-funds check"
./.venv/bin/python -m function_tools_agent.main --scenario agent-as-tool CUST-1001
./.venv/bin/python -m function_tools_agent.main --scenario celery RET-3101
```

What happens:

1. Python starts `function_tools_agent/main.py`.
2. Scenario builds one of four agents:
   - `basic` -> plain function tools in `tools=[...]`
   - `long-running` -> `LongRunningFunctionTool` plus a completion tool
   - `agent-as-tool` -> root `LlmAgent` delegates via `AgentTool`
   - `celery` -> async tool flow via Celery queue + Redis backend
3. For `long-running`, turn 1 returns pending state and function call ID.
4. CLI simulates external approval by sending a `FunctionResponse` in turn 2.
5. Agent finalizes and prints completion markdown.

Short version:

```text
terminal -> function_tools_agent/main.py -> FunctionTool/LongRunningFunctionTool/AgentTool path -> final output
```

### Flow 12: Run the Module 09 helper script

Command:

```bash
./run_function_tools.sh
./run_function_tools.sh long-running
./run_function_tools.sh agent-as-tool RET-3101
./run_function_tools.sh celery RET-3101
```

What happens:

1. Script clears the terminal for readable logs.
2. It runs one scenario or all scenarios in sequence.
3. Each scenario invokes `python -m function_tools_agent.main`.
4. Output shows the scenario banner and final markdown result.

Short version:

```text
run_function_tools.sh -> function_tools_agent/main.py -> module09 scenarios
```

### Flow 13: Run the Module 10 MCP client lesson

Command:

```bash
./.venv/bin/python -m mcp_client.main \
  "CUST-1001: summarize profile and save summary + next action in Redis memory."
```

What happens:

1. Python starts `mcp_client/main.py`.
2. `build_runner()` creates a `Runner` for one `LlmAgent` from `mcp_client/agent.py`.
3. The agent's `tools=[McpToolset(...)]` launches the Redis MCP server process over stdio.
4. During the run, ADK discovers MCP tools and proxies tool calls through the MCP session.
5. The agent stores/retrieves business-banking memory using customer-scoped Redis keys.
6. The same module supports `run_prompt(...)` (blocking) and `stream_prompt(...)` (NDJSON streaming in React UI).

Short version:

```text
terminal or chat UI -> mcp_client/main.py -> LlmAgent + McpToolset -> Redis MCP server -> Redis-backed memory response
```

### Flow 14: Run the Module 11 MCP server lesson

Command:

```bash
./.venv/bin/python -m mcp_server.main \
  "Find the overdraft review operation and generate a mock request."
```

What happens:

1. Python starts `mcp_server/main.py`.
2. `build_runner()` creates a `Runner` for one `LlmAgent` from `mcp_server/agent.py`.
3. The agent builds `McpToolset(...)` using either:
   - `StdioConnectionParams` (default: spawn `python -m mcp_server.server --transport stdio`)
   - `StreamableHTTPConnectionParams` (remote mode: connect to `MODULE11_MCP_HTTP_URL`)
4. The Module 11 MCP server starts, loads OpenAPI specs from `MODULE11_SPECS_DIR` (or `mcp_server/specs/` by default), resolves refs, and builds an operation index at startup.
5. During the run, ADK discovers Module 11 MCP tools such as `search_operations`, `get_operation_details`, `generate_mock_request`, and `generate_mock_response`.
6. The agent uses those tools to search by business language, inspect schemas, and answer with the relevant method/path plus example payloads.
7. The same module supports `run_prompt(...)` (blocking) and `stream_prompt(...)` (NDJSON streaming in the React UI).

Short version:

```text
terminal or chat UI -> mcp_server/main.py -> LlmAgent + McpToolset -> Module 11 MCP server -> OpenAPI index + mock payload tools -> API integration response
```

## The Core Relationship Between Files

Here is the most important mental model:

- `config.py` decides the settings
- `agent.py` creates the ADK agent
- `main.py` runs the agent
- `orchestrate_agent/main.py` can choose a specialist deterministically
- `agent_registry.py` exposes agents to the API and UIs
- `api_app.py` exposes the agents over HTTP
- `streamlit_app.py` gives the user one chat screen
- `ui/src/App.jsx` gives the user another chat screen

You can think of it like this:

```text
Settings -> Agent -> Runner -> Registry -> API/UI
```

More precisely:

```text
config.py -> agent.py -> main.py -> agent_registry.py -> api_app.py -> ui/src/App.jsx
```

## Beginner Python Syntax Guide

This project uses beginner-friendly Python, but there are a few patterns worth learning.

### 1. Imports

Example:

```python
import os
from dataclasses import dataclass
from functools import lru_cache
```

Meaning:

- `import os` imports the whole module
- `from x import y` imports one specific thing from a module

### 2. `from __future__ import annotations`

You see this at the top of several files.

It helps Python handle type hints more cleanly, especially when types refer to classes defined later.

For a beginner, the simplest rule is: leave it there.

### 3. Functions

Example:

```python
def load_environment() -> None:
    load_dotenv(ENV_FILE, override=False)
```

Meaning:

- `def` starts a function
- `load_environment` is the function name
- `() -> None` is a type hint saying this function returns nothing
- indented lines are the function body

### 4. Type Hints

Example:

```python
def create_agent(settings: Settings | None = None) -> Agent:
```

Meaning:

- `settings` can be a `Settings` object or `None`
- `= None` means the default value is `None`
- `-> Agent` means the function returns an `Agent`

Type hints help humans and tools understand the code. They do not change the main logic by themselves.

### 5. Dataclasses

Example:

```python
@dataclass(frozen=True)
class Settings:
    app_name: str
    provider: str
```

Meaning:

- a dataclass is a clean way to store related data
- `frozen=True` means the object should not be changed after creation

This project uses dataclasses for structured data like settings and chat requests.

### 6. Classes

Example:

```python
class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}
```

Meaning:

- a class groups data and behavior together
- `__init__` runs when a new object is created
- `self` means "this object"

In this project, `AgentRegistry` stores available agents.

### 7. Dictionaries

Example:

```python
self._agents[agent.key] = agent
```

A dictionary stores `key -> value` pairs.

Here:

- key: agent key like `"simple_litellm_agent"`
- value: the full `AgentDefinition`

### 8. Lists

Example:

```python
messages.append(user_message)
```

A list stores items in order. `append(...)` adds one item to the end.

### 9. Properties

Example:

```python
@property
def litellm_model(self) -> str:
    return f"{self.provider}/{self.model}"
```

This lets you write:

```python
settings.litellm_model
```

instead of:

```python
settings.litellm_model()
```

It behaves like a field, but it is computed by code.

### 10. F-Strings

Example:

```python
return f"{self.provider}/{self.model}"
```

This is Python string formatting.

If:

- `provider = "openai"`
- `model = "gemini-3-flash-preview"`

Then the result is:

```text
openai/gemini-3-flash-preview
```

### 11. `or` For Default Values

Example:

```python
provider = os.getenv("LITELLM_PROVIDER", "openai").strip() or "openai"
```

This means:

1. read the environment variable
2. if it is missing, use `"openai"`
3. remove extra spaces with `.strip()`
4. if the result is still empty, use `"openai"`

### 12. Caching With `@lru_cache`

Example:

```python
@lru_cache(maxsize=1)
def get_settings() -> Settings:
```

This means Python remembers the result of the function.

Why this helps:

- settings do not need to be rebuilt every time
- the ADK runner does not need to be rebuilt every time

That makes repeated calls faster.

### 13. Exceptions

Example:

```python
except KeyError as exc:
    raise KeyError(...)
```

This means:

- try something
- if a specific error happens, handle it

In this project, it is used to give a clearer error message when an unknown agent key is requested.

### 14. Context Managers

Example:

```python
with st.chat_message("assistant"):
    st.markdown(answer)
```

The `with` block creates a temporary context.

In Streamlit, this tells the UI where the content should appear.

### 15. The `if __name__ == "__main__":` Pattern

Example:

```python
if __name__ == "__main__":
    main()
```

Meaning:

- if the file is run directly, call `main()`
- if the file is imported by another file, do not call `main()`

This is one of the most common Python patterns.

## Key ADK Concepts In This Project

You do not need to learn all of Google ADK at once. This project mainly uses these ideas:

### `Agent`

The agent definition itself.

It contains:

- a name
- a description
- an instruction
- a model

### `LiteLlm`

This is the model adapter.

It connects ADK to an OpenAI-compatible endpoint.

### `Runner`

The runner executes the agent for a user message.

### `InMemorySessionService`

This stores session data in memory while the Python process is alive.

Important beginner note:

- if the process stops, in-memory sessions are lost
- this is fine for a learning project

### Events

ADK returns events while the run is happening.

`extract_final_text()` loops through those events and finds the final assistant response.

## Why The Registry Exists

A beginner might ask: "Why not call the agent directly from `streamlit_app.py`?"

You could, but the registry gives you a cleaner structure.

Benefits:

- the UI does not need to know agent details
- adding new agents becomes easy
- each agent follows the same `run(request) -> str` pattern

This is a small example of separating responsibilities.

## Why The Code Uses Small Functions

This project is nicely split into small units:

- `get_settings()`
- `create_agent()`
- `build_runner()`
- `run_prompt()`
- `extract_final_text()`

That is useful because each function has one job.

This is a good habit in Python:

- easier to read
- easier to test
- easier to reuse

## Beginner-Friendly Trace Example

Suppose you type this in the Streamlit app:

```text
What is Google ADK?
```

The flow is:

1. `streamlit_app.py` gets your text from `st.chat_input(...)`
2. it creates `ChatRequest(prompt=..., user_id=..., session_id=...)`
3. it calls `selected_agent.run(...)`
4. the registry points that call to `_run_simple_litellm_agent(...)`
5. that function calls `run_prompt(...)`
6. `run_prompt(...)` gets the cached runner
7. the runner sends your message to the ADK agent
8. the agent uses `LiteLlm(...)` to call your API endpoint
9. ADK returns events
10. `extract_final_text(...)` returns the assistant's final text
11. Streamlit shows the answer

## Good Places To Experiment Safely

If you want to learn by changing code, these are safe places to start:

### Change the default instruction

Edit `AGENT_INSTRUCTION` handling in `simple_litellm_agent/config.py`.

Try changing:

```text
Answer clearly and briefly.
```

to:

```text
Answer like a friendly Python tutor.
```

### Change the default prompt

Edit `main.py`:

```python
default="Reply with exactly: ok"
```

### Add another registered agent

Duplicate the existing registration pattern in `agent_registry.py`.

This is a good exercise because you will learn:

- dataclasses
- functions
- dictionaries
- app structure

### Change the UI text

Edit labels in `streamlit_app.py`.

This is a low-risk way to get comfortable with Python and Streamlit.

## Common Beginner Questions

### Why is there a package folder with `__init__.py`?

Because `simple_litellm_agent/` is a Python package.

That lets you write imports like:

```python
from simple_litellm_agent.main import run_prompt
```

### Why are some imports inside a function?

Example in `agent_registry.py`:

```python
from simple_litellm_agent.main import run_prompt
```

inside `_run_simple_litellm_agent(...)`.

This can help avoid loading heavier code too early. It also keeps the registry flexible.

### Why use environment variables?

Because secrets and deployment settings should not be hardcoded in source files.

Examples:

- API base URL
- API key
- model name

### Why is the smoke test useful?

Because it checks the integration behavior, not just local Python logic.

It proves the code sends the expected HTTP request.

## Practical Reading Tips For A Python Beginner

When reading any Python file in this project:

1. Start at the imports.
2. Find the dataclasses and classes.
3. Find the public functions.
4. Look for `main()` if it exists.
5. Follow the function calls in order.

A good question to ask at each line is:

```text
Is this defining something, or is this running something?
```

That distinction makes Python code much easier to understand.

## Final Summary

This project is a simple layered app:

- configuration layer: `config.py`
- agent creation layer: `agent.py`
- execution layer: `main.py`
- registration layer: `agent_registry.py`
- API layer: `api_app.py`
- UI layer: `streamlit_app.py` and `ui/src/App.jsx`
- testing layer: `smoke_test.py` and related `tests/` modules

If you understand those layers, you understand the whole project.

The most important beginner lesson from this codebase is not just ADK. It is also software structure:

- keep files focused
- keep functions small
- separate configuration from runtime logic
- keep the API layer separate from the agent logic
- keep UI separate from business logic

If you want, the next useful step would be to expand this guide with diagrams or add inline comments directly into the Python files for learning purposes.
