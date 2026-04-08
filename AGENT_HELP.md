# Agent modules — help reference

This file is the **markdown companion** to the in-app Help panel in the React UI. The overlay reads structured data from `ui/src/help/agentHelp.js`. When you add or change a module, update **both** this file and `agentHelp.js` so they stay aligned.

## Overview

- **Registration:** `agents.json` lists each agent’s `key`, `title`, `description`, `prompt_hint`, `module`, and optionally `supports_streaming`.
- **Runtime:** `agent_registry.py` imports each module and calls `run_prompt(...)`. For streaming agents, it also wires `stream_prompt(...)`.
- **HTTP:** `api_app.py` exposes `GET /api/agents`, `POST /api/chat`, and `POST /api/chat/stream` (NDJSON) when the agent supports streaming.
- **React:** The chat UI loads agents from the API and uses either blocking JSON or NDJSON streaming per agent.

## Module comparison

| Module | `agent_key` | What it does | API surface |
|--------|---------------|--------------|-------------|
| 01 Single Agent | `simple_litellm_agent` | One ADK `Runner`, sync `run()`, one LiteLLM-backed model; full reply when events finish. | `POST /api/chat` |
| 02 Multi Agent | `mulit_agent` | Two specialists on the same topic; results merged into one markdown answer. | `POST /api/chat` |
| 03 Orchestrator | `orchestrate_agent` | Parses `agent_type` (`explain` / `bullet` / `quiz`), runs exactly one matching `Runner`. | `POST /api/chat` |
| 04 Streaming | `streaming_agent` | Same model stack as 01, but `run_async()` yields ADK events; chunks sent as NDJSON lines. | `POST /api/chat/stream` |
| 05 Weather (tools) | `advanced_agent` | Weather-only assistant: Meteosource `place_id` lookup + °C/°F tool; refuses other topics with a fixed message. | `POST /api/chat` or `POST /api/chat/stream` |
| 06 Custom Agent | `custom_agent` | `BaseAgent` keyword router to tech vs general `LlmAgent` children; delegation via `run_async` (no LLM for routing). | `POST /api/chat` or `POST /api/chat/stream` |
| 07 Business Banking | `multi_agent_banking` | `SequentialAgent` pipeline: deposit → bill → decision; mock tools; `demo_expected_decision`; streaming audit trail in UI; optional CLI script. | `POST /api/chat` or `POST /api/chat/stream` |
| 10 MCP Client (Redis banking) | `mcp_client` | Single `LlmAgent` + `McpToolset` (Redis MCP server). Persists and reads customer-scoped business banking memory keys in Redis. | `POST /api/chat` or `POST /api/chat/stream` |

### Module 01 — Single Agent

- **Python package:** `simple_litellm_agent/`
- **Entry:** `simple_litellm_agent.main:run_prompt`

### Module 02 — Multi Agent

- **Python package:** `mulit_agent/`
- **Entry:** `mulit_agent.main:run_prompt`

### Module 03 — Orchestrator

- **Python package:** `orchestrate_agent/`
- **Entry:** `orchestrate_agent.main:run_prompt`
- **Prompt:** Requires an `agent_type:` line and user request (see sidebar prompt hint).

### Module 04 — Streaming Agent

- **Python package:** `streaming_agent/`
- **Entry:** `streaming_agent.main:run_prompt` (blocking) and `streaming_agent.main:stream_prompt` (async generator for the UI)
- **Streaming:** Set `"supports_streaming": true` in `agents.json` for this agent.

### Module 05 — Weather Assistant (tools)

- **Python package:** `advanced_agent/`
- **Entry:** `advanced_agent.main:run_prompt` (blocking) and `advanced_agent.main:stream_prompt` (async generator for NDJSON streaming)
- **Streaming:** Set `"supports_streaming": true` in `agents.json` (already set) so the React UI uses `POST /api/chat/stream`.
- **Tools:** `advanced_agent.weather_tools:fetch_current_weather`, `celsius_to_fahrenheit_display` (see `agent.py` `tools=[...]`, `output_key`)
- **Environment:** Set `WEATHER_API_KEY` in `.env` (Meteosource free tier). The user message supplies the `place_id` (e.g. `calgary`).

### Module 06 — Custom Agent (keyword router)

- **Python package:** `custom_agent/`
- **Entry:** `custom_agent.main:run_prompt` (blocking) and `custom_agent.main:stream_prompt` (NDJSON streaming)
- **Pattern:** `KeywordRoutingAgent` subclasses `BaseAgent`, implements `_run_async_impl`, detects tech keywords in the user message, then delegates with `chosen.run_async(ctx)` (same idea as ADK’s `SequentialAgent`). Two `LlmAgent` children share your LiteLLM settings from `.env`.

### Module 07 — Business Banking (multi-agent)

- **Python package:** `multi_agent_banking/`
- **Entry:** `multi_agent_banking.main:run_prompt` (blocking) and `multi_agent_banking.main:stream_prompt` (NDJSON streaming)
- **Pattern:** `SequentialAgent` runs three `LlmAgent` children in order: `deposit_agent` (deposits + balance movement), `bill_agent` (completed + upcoming bills), and `decision_agent` (overdraft recommendation). Each agent writes to `session.state` via `output_key`; the decision agent reads `{deposit_analysis}` and `{bill_analysis}` from state interpolation in its instruction.
- **Tools:** `banking_tools.py` — `get_monthly_deposits`, `get_balance_movement`, `get_completed_bills`, `get_upcoming_bills`, `get_overdraft_request` (all mock data, no external API).
- **Demo customers:** `CUST-1001` (Acme Corp — healthy profile, teaching outcome **APPROVE**) and `CUST-2002` (Sunrise Bakery — weaker profile, teaching outcome **DENY**).
- **`demo_expected_decision`:** Returned by `get_overdraft_request`. The decision agent’s instructions require its **Decision** line to match this field so the demo stays aligned with the mock profiles even if the model is overly conservative.
- **React UI:** With `supports_streaming: true`, the chat uses `POST /api/chat/stream`. Non-text audit chunks use a `\x00AUDIT:` sentinel in Python; FastAPI emits `{"type":"audit", ...}` NDJSON lines. The UI stores them on the assistant message and renders **Pipeline Audit Trail** (collapsible): per-agent steps, each tool’s **JSON input** and **JSON output summary**, grouped by `agent` on each event.
- **Quick start:** `agents.json` may include a `suggestions` array for this key; the React app shows chips when the thread is empty (e.g. “Acme Corp — healthy profile” → prompt `CUST-1001`).
- **CLI (no UI):** From the repo root, `./run_banking.sh` runs both customers; `./run_banking.sh approve` → `CUST-1001`; `./run_banking.sh deny` → `CUST-2002`. The script calls `python -m multi_agent_banking.main` and prints the same audit-style lines the module’s `__main__` formats. Arguments are lowercased with `tr` for **macOS Bash 3.2** compatibility.
- **Tests:** `tests/multi_agent_banking_smoke_test.py` — mock OpenAI server, both customers, pipeline banner and tool data checks.
- **Further reading:** `README.md` (banking section + project tree), `CODEFLOW.md` (`multi_agent_banking/*`, `run_banking.sh`, Flow 7–8, `App.jsx`), `adk_python_masterclass.html` (Module 07).

### Module 10 — MCP Client (Redis banking)

- **Python package:** `mcp_client/`
- **Entry:** `mcp_client.main:run_prompt` (blocking) and `mcp_client.main:stream_prompt` (NDJSON streaming)
- **Pattern:** One `LlmAgent` with `McpToolset` and `StdioConnectionParams`; the toolset launches a Redis MCP server process and proxies its tools into ADK tool calls.
- **Business use case:** Customer-scoped Redis memory for business banking advisory:
  - `banking:customer:{CUSTOMER_ID}:summary`
  - `banking:customer:{CUSTOMER_ID}:next_action`
- **Environment:** Configure MCP process with `MODULE10_MCP_COMMAND`, `MODULE10_MCP_ARGS`, and optional `MODULE10_MCP_TIMEOUT`.
- **React UI:** Registered in `agents.json` with `supports_streaming: true`, so the same chat UI can run this MCP lesson via `POST /api/chat/stream`.

## Adding a new agent or module

1. Create a Python package (e.g. `my_agent/`) with `agent.py` (ADK agent) and `main.py` exposing **`run_prompt(prompt, user_id=..., session_id=...)`** returning a string.
2. **Optional streaming:** If the UI should stream tokens, add **`async def stream_prompt(...)`** in `main.py` and set `"supports_streaming": true` in `agents.json`.
3. Add an entry to **`agents.json`** with a unique `key` and `module` path (e.g. `my_agent.main`).
4. Append a row to **`HELP_MODULES`** in `ui/src/help/agentHelp.js` and extend this **`AGENT_HELP.md`** (comparison table + short subsection).
5. Restart the API and reload the React app.

## In-app Help

- Open the **Help** button (ⓘ) next to **New conversation** in the sidebar, or press **Ctrl+H** anywhere in the chat UI.
- The help window uses a **left menu**: **Overview** explains registration and wiring; each **module** opens its own detail pane (runner pattern and HTTP surface) so you can extend the list in `agentHelp.js` without a long scrolling page.
- **Escape** or click outside the dialog to close.
