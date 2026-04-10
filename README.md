# Simple Google ADK agents with API and UIs

This project shows a small but useful **Google Agent Development Kit (ADK)** learning project that sends requests to a **LiteLLM / OpenAI-compatible** `/v1/chat/completions` endpoint.

It now includes:

- the Python agent modules (including Module 06: a `BaseAgent` keyword router in `custom_agent/`, Module 07: a multi-agent business banking pipeline in `multi_agent_banking/`, Module 08: workflow orchestration patterns in `workflow_agent/`, Module 09: function-tool patterns in `function_tools_agent/`, Module 10: MCP client + Redis banking memory in `mcp_client/`, and Module 11: a custom OpenAPI-backed MCP server in `mcp_server/`)
- a FastAPI layer that exposes those agents over HTTP
- the original Streamlit UI
- a React + Vite + Tailwind chat UI that talks to the API
- `run_banking.sh` — optional CLI for Module 07 (business banking pipeline without the API or UI)
- `run_workflow.sh` — optional CLI for Module 08 (workflow-agent scenarios without the API or UI)

It is designed for your kind of setup, where you have:

- an API base URL
- an API key
- a model name

For example, your endpoint might support a request like:

```bash
curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer not-needed" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash-preview",
    "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
    "max_tokens": 32
  }'
```

In this ADK example, the same connection details are provided through environment variables and passed into `LiteLlm(...)`.

## Project structure

```text
adk-masterclass/
├── AGENT_HELP.md
├── api_app.py
├── agents.json
├── agent_registry.py
├── run.sh
├── run_banking.sh
├── run_function_tools.sh
├── run_workflow.sh
├── runstreamlit.sh
├── streamlit_app.py
├── .env.example
├── README.md
├── CODEFLOW.md
├── requirements.txt
├── tests/
│   ├── api_smoke_test.py
│   ├── smoke_test.py
│   ├── mulit_agent_smoke_test.py
│   ├── orchestrate_agent_smoke_test.py
│   ├── multi_agent_banking_smoke_test.py
│   ├── mcp_server_loader_smoke_test.py
│   ├── mcp_server_mock_payload_test.py
│   └── agent_registry_smoke_test.py
├── ui/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── help/
│       │   ├── agentHelp.js
│       │   └── HelpOverlay.jsx
│       └── App.jsx
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
└── simple_litellm_agent/
    ├── __init__.py
    ├── agent.py
    ├── config.py
    └── main.py
```

## Agent help

- **[`AGENT_HELP.md`](AGENT_HELP.md)** — Markdown reference for all registered modules: comparison table, how `agents.json` and the API fit together, and a checklist for **adding a new agent**. Edit this when you add modules so the docs stay accurate.
- **`ui/src/help/agentHelp.js`** — Structured data (`HELP_META`, `HELP_MODULES`) used by the React **Help** overlay. Update this when you add an entry to `agents.json` and want it to appear in the sidebar Help panel.
- **`ui/src/help/HelpOverlay.jsx`** — Help dialog with a **sidebar** (Overview + one entry per module) and a **single detail pane**; opened with the **ⓘ** button next to **New conversation**. Dismiss with **Escape** or a click on the backdrop.

Keep **`AGENT_HELP.md`** and **`agentHelp.js`** aligned whenever you add or rename a module.

## What each file does

- `simple_litellm_agent/config.py`
  - Loads `.env`
  - Reads `LITELLM_API_BASE`, `LITELLM_API_KEY`, `LITELLM_MODEL`, `LITELLM_PROVIDER`, and `LITELLM_MAX_TOKENS`
  - Normalizes the API base so both `http://127.0.0.1:4000` and `http://127.0.0.1:4000/v1` work

- `simple_litellm_agent/agent.py`
  - Creates the ADK `root_agent`
  - Connects the agent model to `LiteLlm(...)`

- `simple_litellm_agent/main.py`
  - Creates a session
  - Runs the agent with a prompt
  - Prints the final answer

- `mulit_agent/agent.py`
  - Creates two simple ADK agents
  - One writes 2 short paragraphs
  - One returns 3 bullet points

- `mulit_agent/main.py`
  - Runs both agents for the same topic
  - Combines the two answers into one markdown response

- `orchestrate_agent/agent.py`
  - Creates 3 simple ADK specialist agents
  - Supports `explain`, `bullet`, and `quiz`
  - Keeps the specialist descriptions and instructions easy to inspect

- `orchestrate_agent/main.py`
  - Reads `agent_type` from the prompt
  - Routes deterministically to the matching specialist
  - Adds `Agent type intent: ...` to the routed prompt so the selected agent knows why it was chosen

- `streaming_agent/agent.py`
  - Module 04: defines a single `streaming_agent` with a multi-sentence instruction and a higher `max_tokens` floor so answers are not cut off mid-stream

- `streaming_agent/main.py`
  - Exposes `run_prompt(...)` for the usual blocking path (Streamlit, `POST /api/chat`, CLI)
  - Exposes async `stream_prompt(...)` that iterates `Runner.run_async()` and yields text chunks for `POST /api/chat/stream`

- `advanced_agent/weather_tools.py`
  - Module 05: `fetch_current_weather(place_id)` calls the Meteosource free `/point` API (`WEATHER_API_KEY` from `.env`)
  - `celsius_to_fahrenheit_display(celsius)` returns both °C and °F for the assistant reply

- `advanced_agent/agent.py`
  - Module 05: ADK `Agent` with those two Python functions in `tools=[...]`, `output_key`, and instructions that refuse non-weather questions with a fixed sentence

- `advanced_agent/main.py`
  - Blocking `run_prompt(...)` and async `stream_prompt(...)` (NDJSON via `POST /api/chat/stream` when `supports_streaming` is true in `agents.json`)

- `custom_agent/agent.py`
  - Module 06: `KeywordRoutingAgent(BaseAgent)` with two `LlmAgent` children; `_run_async_impl` routes on keywords then delegates via `run_async(ctx)` (same delegation pattern as ADK’s `SequentialAgent`)

- `custom_agent/main.py`
  - Blocking `run_prompt(...)` and async `stream_prompt(...)` for the API and React chat UI

- `multi_agent_banking/banking_tools.py`
  - Module 07: mock banking data and tool functions — deposit transactions, daily balances, completed bills, upcoming bills, and overdraft request details for two demo customers (`CUST-1001` Acme Corp, `CUST-2002` Sunrise Bakery). `get_overdraft_request` also returns `demo_expected_decision` (`APPROVE` vs `DENY`) so the credit decision matches the intended teaching profile instead of varying with the LLM.

- `multi_agent_banking/agent.py`
  - Module 07: `SequentialAgent` pipeline with three `LlmAgent` children: `deposit_agent` (cash-flow), `bill_agent` (obligations), `decision_agent` (overdraft approval). Each agent writes to `session.state` via `output_key`; the decision agent reads prior analyses.

- `multi_agent_banking/main.py`
  - Blocking `run_prompt(...)` and async `stream_prompt(...)` for the API and React chat UI. Collects output from all three pipeline stages and streams them as a combined response. The streaming path also emits **audit trail events** (agent transitions, tool calls with inputs, tool results with key metrics) that the React UI renders as a live-updating pipeline timeline.

- `workflow_agent/workflow_tools.py`
  - Module 08: mock retail deposit platform data and tools for workflow scenarios — profile/deposit lookups, AML and velocity checks, exception queue handling for looped reconciliation, and a deterministic `demo_expected_offer` for the final composition decision.

- `workflow_agent/agent.py`
  - Module 08: builds three workflow patterns:
    - `LoopAgent` for repeated deposit exception handling (`fetch_next_deposit_exception` + `clear_deposit_exception`)
    - `ParallelAgent` for concurrent deposit-health and compliance/risk assessments
    - Composition pattern: `SequentialAgent(ParallelAgent -> LoopAgent -> final_offer_agent)`

- `workflow_agent/main.py`
  - CLI-focused Module 08 runner with `run_prompt(..., scenario=loop|parallel|composition)`, per-scenario runner caching, and no `agents.json` registration (intentionally no API/UI wiring for this lesson).

- `function_tools_agent/function_tools.py`
  - Module 09: custom function tools built on top of existing datasets (`workflow_agent` + `multi_agent_banking`), plus a long-running approval starter/finalizer and a Celery+Redis-backed async task tool pair (`submit_deposit_recalc_task`, `get_deposit_recalc_task_status`).

- `function_tools_agent/agent.py`
  - Module 09: three agent setups:
    - basic function tools (`tools=[python_functions...]`)
    - long-running function tools (`LongRunningFunctionTool`)
    - agent-as-a-tool (`AgentTool` with `skip_summarization=True`)
    - celery-backed async tool scenario (`create_celery_banking_agent`)

- `function_tools_agent/main.py`
  - Module 09 runner with `--scenario basic|long-running|agent-as-tool|celery`. The long-running scenario demonstrates a two-turn flow: pending tool call, then a synthetic approval `FunctionResponse` to resume and complete.

- `mcp_client/agent.py`
  - Module 10: single business-banking `LlmAgent` with `McpToolset` + `StdioConnectionParams` to a Redis MCP server process (configured by env vars).

- `mcp_client/main.py`
  - Module 10: blocking `run_prompt(...)` and async `stream_prompt(...)`, so this MCP lesson is stitched into the same API + React chat flow as the streaming modules.

- `mcp_server/server.py`
  - Module 11: FastMCP server that loads OpenAPI specs from a folder during startup, exposes search/detail/mock tools, and can run over `stdio` or `streamable-http`.

- `mcp_server/openapi_loader.py`
  - Module 11: parses `.json` / `.yaml` / `.yml` OpenAPI files, resolves internal `$ref` pointers, and builds an operation-centric in-memory index keyed by `operationId`.

- `mcp_server/mock_payloads.py`
  - Module 11: deterministic schema-to-example generator used for mock request and response payloads.

- `mcp_server/agent.py`
  - Module 11: ADK `LlmAgent` with `McpToolset` that connects to the local stdio server by default, or to a remote streamable HTTP MCP server when configured by env vars.

- `mcp_server/main.py`
  - Module 11: blocking `run_prompt(...)` and async `stream_prompt(...)`, so the custom MCP server lesson is stitched into the same API + React chat flow as Modules 04, 05, 06, 07, and 10.

- `agents.json`
  - Stores the agent list for the UI
  - Keeps beginner-friendly metadata outside Python code
  - Now also stores `prompt_hint` text for the UI
  - Optional `supports_streaming` flag: when `true`, the module must also define async `stream_prompt(...)` for NDJSON streaming

- `agent_registry.py`
  - Loads agents from `agents.json`
  - Imports each module and calls its `run_prompt(...)` function
  - Wires `stream_prompt(...)` when `supports_streaming` is set
  - Exposes `prompt_hint` so the UI can show how to talk to each agent
  - Keeps the Streamlit app and the API reusable as you add more agents later

- `api_app.py`
  - Exposes the registered agents over HTTP
  - Adds `GET /api/agents` so UIs can discover the available agents (includes `supports_streaming` per agent)
  - Adds `POST /api/chat` so browser and API clients can run a selected agent
  - Adds `POST /api/chat/stream` for NDJSON token streaming when the selected agent supports it

- `run.sh`
  - Starts the FastAPI server (port **8512**) and the Vite dev server (port **8513**) together

- `runstreamlit.sh`
  - Optional: starts the Streamlit UI on port **8511** (frees a stale listener first)

- `run_workflow.sh`
  - Optional: runs Module 08 workflow scenarios from the terminal
  - Supports `loop`, `parallel`, `composition`, or `all`
  - Supports customer aliases (`strong`/`healthy` -> `RET-3101`, `weak`/`risk`/`week` -> `RET-4420`; `week` catches a common typo for weak)
  - Keeps workflow exercises independent of API/React wiring

- `run_function_tools.sh`
  - Optional: runs Module 09 function tool demos from the terminal
  - Supports `basic`, `long-running`, `agent-as-tool`, `celery`, or `all`
  - Keeps Module 09 as a CLI teaching module (no UI wiring required)

- `tests/agent_registry_smoke_test.py`
  - Checks that the registry loads the same agents defined in `agents.json`
  - Confirms unknown agent keys fail clearly
  - Verifies prompt hints are loaded too

- `streamlit_app.py`
  - Provides a Streamlit chat interface
  - Lets you pick an agent from the sidebar
  - Keeps a separate chat history per selected agent
  - Shows the per-agent prompt hint in the sidebar and chat box

- `ui/`
  - Contains the React + Vite + Tailwind chat app
  - Loads agent metadata from `GET /api/agents`
  - Sends prompts to `POST /api/chat`, or to `POST /api/chat/stream` when the agent has `supports_streaming: true`, and appends chunks to the assistant bubble as they arrive
  - Mirrors the same per-agent session idea as the Streamlit UI

- `tests/api_smoke_test.py`
  - Starts a tiny local mock server
  - Calls the FastAPI routes with `TestClient`
  - Verifies the API can list agents and run a chat request end to end

- `tests/smoke_test.py`
  - Starts a tiny local mock server
  - Verifies the ADK agent really sends a request to `/v1/chat/completions`
  - Confirms the request contains your model name and bearer token

- `tests/mulit_agent_smoke_test.py`
  - Starts a tiny local mock server for the new multi-agent example
  - Verifies both agents send requests for the same topic
  - Confirms the combined response contains both sections

- `tests/orchestrate_agent_smoke_test.py`
  - Starts a tiny local mock server for the Module 03 orchestrator
  - Verifies each `agent_type` routes to the correct specialist
  - Confirms the routed prompt includes the explicit agent type intent

- `tests/multi_agent_banking_smoke_test.py`
  - Starts a mock server for the Module 07 banking pipeline (port 4015)
  - Runs both demo customers (`CUST-1001` and `CUST-2002`) through the full pipeline
  - Validates mock tool data (deposit counts, balance ranges, bill totals)
  - Confirms the pipeline banner includes all three agent names
  - Verifies invalid customer IDs return clear error messages

## How the wiring works

The important part is this:

```text
model=LiteLlm(
    model="openai/gemini-3-flash-preview",
    api_base="http://127.0.0.1:4000/v1",
    api_key="your-api-key",
    max_tokens=32,
)
```

### Why `openai/...`?

Because your LiteLLM endpoint is exposing an **OpenAI-compatible API**.

So even if the actual backend model is Gemini, the LiteLLM client is told to talk using the OpenAI-compatible provider adapter:

- provider: `openai`
- model name sent to the endpoint: `gemini-3-flash-preview`

That becomes:

- LiteLLM model string: `openai/gemini-3-flash-preview`
- HTTP request model field: `gemini-3-flash-preview`

## Setup

### 1. Install dependencies

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m pip install -r requirements.txt
```

### 2. Create your `.env`

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
cp .env.example .env
```

Then edit `.env` and set:

```dotenv
LITELLM_API_BASE=http://127.0.0.1:4000/v1
LITELLM_API_KEY=not-needed
LITELLM_MODEL=gemini-3-flash-preview
LITELLM_PROVIDER=openai
LITELLM_MAX_TOKENS=32
```

If your local proxy ignores auth, using a placeholder token like `not-needed` is usually fine.

## Run the agent

### Default prompt

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m simple_litellm_agent.main
```

### Custom prompt

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m simple_litellm_agent.main "Tell me in one sentence what Google ADK is."
```

## Run the multi-agent module

This is the Module 02 learning example: two independent agents that both receive the same topic.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m mulit_agent.main "Artificial intelligence in education"
```

## Run the orchestrator module

This is the Module 03 learning example: one deterministic orchestrator routes to 3 specialist agents based on the `agent_type` line in the prompt.

Supported values:

- `explain`
- `bullet`
- `quiz`

Example:

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m orchestrate_agent.main $'agent_type: explain\nrequest: Explain what an agent orchestrator does.'
```

The prompt format matters because the orchestrator reads the explicit `agent_type` first, then forwards a routed prompt that includes:

```text
Agent type intent: explain
User request: Explain what an agent orchestrator does.
```

## Run the streaming agent module

This is the Module 04 learning example: ADK streams assistant tokens through `Runner.run_async()`. The React chat UI reads newline-delimited JSON from `POST /api/chat/stream` so the answer appears incrementally.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m streaming_agent.main
```

That command prints chunks to the terminal as they arrive (`print(..., flush=True)` style). For the browser experience, select **Streaming Agent** in the React UI (or call the streaming endpoint directly).

## Run the weather assistant (Module 05 — tools)

This module is the **LLM Agent — Full Feature Breakdown** lesson: plain Python functions registered as ADK tools, plus `output_key` on the agent.

1. Add your Meteosource API key to `.env` as `WEATHER_API_KEY` (see `.env.example`). The free tier uses the `point` endpoint with `place_id` (for example `calgary`, `london`).
2. Run the agent from the CLI:

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m advanced_agent.main "What is the weather in calgary?"
```

In the React chat UI, select **Weather Assistant (tools)**. The UI streams assistant tokens over `POST /api/chat/stream` (same pattern as Module 04). Ask only weather-related questions; other topics receive a short refusal message. The model calls `fetch_current_weather` and `celsius_to_fahrenheit_display` so the reply can include conditions, summary, and temperature in both Celsius and Fahrenheit.

**Troubleshooting:** The weather tool reloads `WEATHER_API_KEY` from `.env` on each call (so you do not have to restart the API only for that key). If the assistant bubble stays empty for a long time, the delay is usually the LiteLLM/model round-trip or tool loop, not Meteosource — confirm your `LITELLM_*` settings and that the model supports tool calling. Weather API failures are logged at **warning** level on the uvicorn process. Restart the API if you change other env vars that are read only at startup (for example `LITELLM_API_BASE`).

## Run the custom agent (Module 06 — BaseAgent)

This module is the **Custom Agent — BaseAgent Subclass** lesson: a `KeywordRoutingAgent` implements `_run_async_impl`, inspects the user message for tech-related keywords (for example `python`, `code`, `api`), and forwards the invocation to either a **tech** or **general** `LlmAgent`. Routing is rule-based — no extra LLM call to choose a branch.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m custom_agent.main "How do I use Python type hints?"
```

In the React chat UI, select **Custom Agent (keyword router)**. The UI streams assistant tokens over `POST /api/chat/stream` (same pattern as Modules 04 and 05). Try a general prompt without tech keywords (for example a book recommendation) to see the general specialist.

## Run the business banking pipeline (Module 07 — multi-agent)

This module is the **Multi-Agent Systems** lesson: a `SequentialAgent` runs three specialist `LlmAgent` children in order — `deposit_agent` (analyzes deposit transactions and balance movement), `bill_agent` (reviews completed and upcoming bills), and `decision_agent` (recommends overdraft approval or denial). All data is mocked — no external banking API needed.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass

# Run a single customer directly:
./.venv/bin/python -m multi_agent_banking.main CUST-1001

# Or use the helper script for both approve & deny scenarios:
./run_banking.sh              # runs CUST-1001 then CUST-2002
./run_banking.sh approve      # only the healthy profile (CUST-1001)
./run_banking.sh deny         # only the weaker  profile (CUST-2002)
```

Try `CUST-2002` for a customer with a weaker cash-flow profile. In the React chat UI, select **Business Banking (multi-agent)** and type a customer ID, or use the **Quick start** suggestion chips (`CUST-1001` / `CUST-2002`). The pipeline streams each agent's analysis as it completes. A **Pipeline Audit Trail** panel appears above the reply: per-agent steps, each tool’s **full JSON input** and **output summary**, updating live during streaming.

**Teaching outcomes (mock data):** `get_overdraft_request` returns `demo_expected_decision` — `APPROVE` for `CUST-1001` and `DENY` for `CUST-2002` — so the decision agent’s markdown matches the intended scenario even when the model is conservative.

**Docs for this module:** [`AGENT_HELP.md`](AGENT_HELP.md) (Module 07), [`CODEFLOW.md`](CODEFLOW.md) (`multi_agent_banking/*`, `run_banking.sh`, Flow 7–8), and the **Module 07** section in [`adk_python_masterclass.html`](adk_python_masterclass.html). In-app **Help** (Ctrl+H) mirrors `agentHelp.js`.

**CLI note:** `run_banking.sh` uses `tr` for case-insensitive arguments so it works on **macOS default Bash 3.2** (no `${var,,}`).

## Run workflow agents (Module 08 — retail deposit workflows)

This lesson implements ADK workflow orchestrators for a modern retail deposit platform and keeps it CLI-only by design (not registered in `agents.json`).

- **LoopAgent:** cycles through pending deposit exceptions and clears one per iteration.
- **ParallelAgent:** runs deposit-health analysis and compliance/risk checks concurrently.
- **Composition Pattern:** nests workflow agents as `ParallelAgent -> LoopAgent -> final_offer_agent`.

The CLI prints an **audit trail** (agent start/end, tool calls with JSON arguments, tool results with short summaries), then the final assistant response. Pass **`--quiet`** to print only the final text. `run_workflow.sh` clears the screen at startup (via `clear`, with a terminal escape fallback).

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass

# Run a single scenario directly:
./.venv/bin/python -m workflow_agent.main RET-3101 --scenario composition
./.venv/bin/python -m workflow_agent.main RET-4420 --scenario parallel
./.venv/bin/python -m workflow_agent.main RET-3101 --scenario loop --quiet

# Or use the helper script:
./run_workflow.sh                         # all scenarios for RET-3101
./run_workflow.sh loop weak               # loop scenario for RET-4420
./run_workflow.sh loop week               # same as weak (typo-friendly alias)
./run_workflow.sh composition strong      # composition for RET-3101
```

**Teaching outcomes (mock data):** the composition decision step calls `get_deposit_offer_request`, and the instructions force `Recommended Offer` to match tool field `demo_expected_offer` so outputs stay deterministic (`PREMIUM_PLUS` for `RET-3101`, `SAFE_GROWTH` for `RET-4420`).

## Run custom function tools (Module 09)

This lesson extends Module 09 with runnable examples for:

- **Function Tools:** plain Python functions in `tools=[]`
- **Long Running Function Tools:** `LongRunningFunctionTool` for async approval-style operations
- **Agent-as-a-Tool:** delegate from one `LlmAgent` to another via `AgentTool`
- **Celery + Redis tool:** queue async banking recalculation jobs and poll status/results

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass

# Direct module run:
./.venv/bin/python -m function_tools_agent.main --scenario basic RET-3101
./.venv/bin/python -m function_tools_agent.main --scenario long-running \
  "Request manual approval for RET-4420 due to source-of-funds check"
./.venv/bin/python -m function_tools_agent.main --scenario agent-as-tool RET-3101
./.venv/bin/python -m function_tools_agent.main --scenario celery RET-3101
./.venv/bin/python -m function_tools_agent.main --scenario celery --show-tool-events RET-3101
./.venv/bin/python -m function_tools_agent.main --scenario celery --show-tool-events --poll-task RET-3101
./.venv/bin/python -m function_tools_agent.main --scenario celery --status-grace-seconds 3 RET-3101

# Helper script:
./run_function_tools.sh
./run_function_tools.sh long-running
./run_function_tools.sh agent-as-tool CUST-1001
./run_function_tools.sh celery RET-3101
```

**Implementation note:** Module 09 reuses existing mock datasets from Module 07 and Module 08 so examples stay aligned with the banking domain already built in this repo.

**Celery setup (optional for `celery` scenario):**

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/pip install "celery[redis]"
docker run --rm -p 6379:6379 redis:7
./.venv/bin/celery -A function_tools_agent.function_tools:celery_app worker -Q module09_banking_tasks -l info
```

**Use existing remote Redis (IP/port):** set either a full URL or host/port fields in `.env`:

```dotenv
# Preferred
MODULE09_CELERY_REDIS_URL=redis://:your-password@10.20.30.40:6380/0

# Fallback if URL not set
MODULE09_REDIS_HOST=10.20.30.40
MODULE09_REDIS_PORT=6380
MODULE09_REDIS_DB=0
MODULE09_REDIS_PASSWORD=your-password
```

**How to get completion status:**
- Use `--show-tool-events` to print `task_id`.
- Use `--poll-task` to auto-check until ready.
- Without `--poll-task`, the app can do a one-time wait + follow-up check via `--status-grace-seconds` (default `3`), which reduces immediate `PENDING` replies.

**If you see** `Received unregistered task of type 'module09.recalc_deposit_score'`: restart the Celery worker so updated task registration loads.

## Run MCP client (Module 10 — Redis MCP, business banking)

This lesson uses ADK as an MCP client. A single agent connects to a Redis MCP server and persists customer banking memory (summary + next action) under customer-scoped Redis keys.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass

# Configure MCP process in .env (defaults shown):
# MODULE10_MCP_COMMAND=uvx
# MODULE10_MCP_ARGS=--from redis-mcp-server@latest redis-mcp-server
# MODULE10_MCP_TIMEOUT=20

./.venv/bin/python -m mcp_client.main \
  "CUST-1001: summarize profile and save summary + next action in Redis memory."
```

In the React chat UI, select **MCP Client (Redis banking)**. This agent is registered in `agents.json` with `supports_streaming: true`, so the UI runs it through `POST /api/chat/stream`.

## Run MCP server (Module 11 — OpenAPI explorer)

This lesson builds your own MCP server. The server loads OpenAPI specs from a configured folder, indexes operations by `operationId`, and exposes tools for search, schema inspection, and mock request/response generation.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass

# Default path: stdio-backed Module 11 agent (the agent spawns the MCP server itself)
./.venv/bin/python -m mcp_server.main \
  "Find the customer profile operation and generate a mock response."
```

Optional direct server runs:

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass

# Local stdio server
./.venv/bin/python -m mcp_server.server --transport stdio --print-config

# Remote streamable HTTP server
./.venv/bin/python -m mcp_server.server \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8765 \
  --http-path /mcp
```

Useful env vars:

- `MODULE11_SPECS_DIR` — folder scanned at startup for `.json`, `.yaml`, and `.yml` OpenAPI specs
- `MODULE11_MCP_TRANSPORT=stdio|streamable-http` — how the ADK agent connects to the server
- `MODULE11_MCP_HTTP_URL` — remote streamable HTTP URL when transport is `streamable-http`

If `MODULE11_SPECS_DIR` is empty, Module 11 uses the bundled demo spec in `mcp_server/specs/`.

In the React chat UI, select **MCP Server (OpenAPI explorer)**. This agent is also registered in `agents.json` with `supports_streaming: true`, so the same chat UI can drive the custom MCP server lesson over `POST /api/chat/stream`.

## Run the API

This is the shared backend layer for browser clients and any other HTTP-based consumer.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m uvicorn api_app:app --host 127.0.0.1 --port 8512 --reload
```

Useful endpoints:

- `GET /health`
- `GET /api/agents`
- `POST /api/chat`
- `POST /api/chat/stream` (NDJSON; only for agents with `supports_streaming: true` in `agents.json`)

Example:

```bash
curl -sS http://127.0.0.1:8512/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "simple_litellm_agent",
    "prompt": "What is Google ADK?",
    "user_id": "curl-user"
  }'
```

## Run the Streamlit chat UI (optional)

The main browser UI is React + Vite; Streamlit is an optional Python-only alternative that talks to the agents directly (not via the FastAPI layer).

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./runstreamlit.sh
```

Or run Streamlit yourself:

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/streamlit run streamlit_app.py --server.port 8511
```

What you get:

- a sidebar agent picker
- a chat window for the selected agent
- a separate session per agent
- a prompt hint for the selected agent
- a reusable UI you can keep using as you add more agent modules
- the new Module 03 orchestrator option in the sidebar

## Run the React chat UI

Start the API first, then run the Vite app:

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass/ui
npm install
npm run dev
```

By default Vite listens on **port 8513** and proxies `/api` requests to `http://127.0.0.1:8512`.

If you want the browser to call a different backend directly, create `ui/.env` from `ui/.env.example` and set:

```dotenv
VITE_AGENT_API_BASE_URL=http://127.0.0.1:8512/api
VITE_DEV_API_PROXY_TARGET=http://127.0.0.1:8512
```

### Run API + React together

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./run.sh
```

This frees stale listeners, then starts the agent API (**8512**) and the React dev server (**8513**). Use `./runstreamlit.sh` in a separate terminal if you also want the optional Streamlit UI (**8511**).

### Add more agents later

When you create another agent, you do not need to rebuild the UI.
Just:

1. create the new agent module
2. add one entry in `agents.json`
3. set its `module` value to the Python module that exposes `run_prompt(...)`
4. optionally add a `prompt_hint`
5. if you want the React app to stream tokens, set `"supports_streaming": true` and implement async `stream_prompt(...)` in that module (see `streaming_agent/main.py`)
6. reload the React app (or restart `./runstreamlit.sh` if you use Streamlit)

Example shape:

```json
{
  "agents": [
    {
      "key": "my_next_agent",
      "title": "My Next Agent",
      "description": "My next learning experiment.",
      "prompt_hint": "Optional text shown in the UI.",
      "module": "my_next_agent.main",
      "supports_streaming": false
    }
  ]
}
```

### Show a timing breakdown

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python -m simple_litellm_agent.main --timing "Reply with exactly: ok"
```

You can also enable timing with an environment variable:

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
ADK_SHOW_TIMING=1 ./.venv/bin/python -m simple_litellm_agent.main "Reply with exactly: ok"
```

The timing output shows:

- `runner_setup`: one-time local setup inside the Python process
- `run_call`: the initial ADK runner call
- `consume_events`: the time spent consuming ADK events until the final answer arrives
- `total`: end-to-end time inside `run_prompt(...)`

## Run the smoke test

This test does **not** require your real LiteLLM server. It spins up a tiny fake server locally and confirms the ADK agent sends the correct OpenAI-style request.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python tests/smoke_test.py
```

## Run the multi-agent smoke test

This test also uses a fake local server, but it verifies that the multi-agent example makes **two** calls: one for the paragraph agent and one for the bullet-point agent.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python tests/mulit_agent_smoke_test.py
```

## Run the orchestrator smoke test

This test uses a fake local server and verifies all 3 deterministic routes: `explain`, `bullet`, and `quiz`.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python tests/orchestrate_agent_smoke_test.py
```

## Run the banking pipeline smoke test

This test uses a fake local server and verifies the Module 07 multi-agent banking pipeline. It runs both demo customers (`CUST-1001` and `CUST-2002`), checks the pipeline banner, validates mock tool data, and confirms invalid customer IDs produce clear errors.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python tests/multi_agent_banking_smoke_test.py
```

## Run the Module 11 OpenAPI loader smoke test

This test creates a temporary OpenAPI spec, verifies `$ref` resolution, checks operation search, and confirms the synthetic `operationId` fallback works when a spec omits one.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python tests/mcp_server_loader_smoke_test.py
```

## Run the Module 11 mock payload test

This test uses the bundled demo spec in `mcp_server/specs/` and verifies that mock request and response payloads are generated from resolved schemas.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python tests/mcp_server_mock_payload_test.py
```

## Run the registry smoke test

This verifies that `agent_registry.py` loads its menu from `agents.json` correctly.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python tests/agent_registry_smoke_test.py
```

## Run the API smoke test

This verifies that the FastAPI wrapper can list agents and execute a chat call while still talking to the same mock OpenAI-style backend.

```bash
cd /Users/sathishkr/PycharmProjects/adk-masterclass
./.venv/bin/python tests/api_smoke_test.py
```

Expected result:

- final response is `ok`
- request path is `/v1/chat/completions`
- bearer token is included
- model is `gemini-3-flash-preview`

## Minimal learning summary

To create a simple ADK agent with a LiteLLM-compatible endpoint, you need only 4 ideas:

1. **Create an ADK agent**
   - `Agent(...)`
2. **Use LiteLLM as the model adapter**
   - `LiteLlm(...)`
3. **Pass API URL, API key, and model**
   - `api_base=...`
   - `api_key=...`
   - `model="openai/<your-model>"`
4. **Run it with a Runner + Session**
   - `Runner(...)`
   - `InMemorySessionService()`

## Core example

```python
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

root_agent = Agent(
    name="root_agent",
    description="A tiny ADK agent",
    instruction="You are a helpful assistant.",
    model=LiteLlm(
        model="openai/gemini-3-flash-preview",
        api_base="http://127.0.0.1:4000/v1",
        api_key="not-needed",
        max_tokens=32,
    ),
)
```

## Optional next steps

After this beginner example works, a good next step is to add:

- one custom tool
- one multi-turn session
- `adk web` for UI-based testing
- a second agent for delegation

If you want, I can next turn this into:

1. a **tool-using ADK agent**, or
2. a **multi-agent ADK example**, or
3. an **`adk web` runnable layout**.

## Tips to improve response time

If responses feel slow, these are usually the biggest wins:

1. **Keep the Python process alive**
   - This project now caches the ADK `Runner` and settings per process.
   - The first request in a process is the slowest.
   - Later calls in the same process avoid rebuilding the runner.

2. **Avoid eager imports**
   - The package no longer creates the agent at import time.
   - That reduces startup overhead and makes environment-variable changes safer.

3. **Use a low-latency model**
   - Faster models make a much bigger difference than Python-side micro-optimizations.
   - For your setup, a `flash`-class model is usually the right choice.

4. **Keep `LITELLM_MAX_TOKENS` small**
   - If you only want short answers like `ok`, keep this low.
   - Example:

   ```text
   LITELLM_MAX_TOKENS=16
   ```

5. **Keep prompts and session history short**
   - More tokens means slower requests.
   - If you reuse the same session for many turns, later turns can become slower.

6. **Measure before optimizing**
   - If `runner_setup` is small but `consume_events` is large, the delay is mostly your LiteLLM proxy, model, or network.
   - If `runner_setup` is large, prefer a long-running process rather than starting Python for every prompt.
