/**
 * Single source for the in-app Help overlay (React) and the canonical copy in /AGENT_HELP.md.
 *
 * When you add a new agent module:
 * 1. Implement Python under e.g. `my_agent/` with `run_prompt(...)` in `my_agent/main.py`.
 * 2. Register it in `agents.json` (and `supports_streaming` + `stream_prompt` if applicable).
 * 3. Append a new entry to `HELP_MODULES` below with the same `agentKey` as in `agents.json`.
 * 4. Update `AGENT_HELP.md` in the repo root to match (keep the markdown doc in sync).
 */

/** @typedef {{ module: string, title: string, agentKey: string, pattern: string, apiSurface: string, supportsStreaming?: boolean }} HelpModuleEntry */

export const HELP_NAV = {
  /** Sentinel id for the overview pane (not an agent key). */
  overviewId: 'overview',
}

export const HELP_META = {
  eyebrow: 'ADK masterclass',
  title: 'Help',
  /** Left nav label for the intro pane. */
  overviewNavLabel: 'Overview',
  sectionModules: 'Modules — how they differ',
  /** Text before the highlighted agents.json filename in the intro paragraph. */
  introBeforeAgentsFile: 'Agents are registered in ',
  /** Text after agents.json in the intro paragraph. */
  introAfterAgentsFile:
    '. The FastAPI app imports each module and calls run_prompt(...). The React chat loads GET /api/agents and sends POST /api/chat, or POST /api/chat/stream when supports_streaming is true.',
  /** Shown only on the Overview pane under the intro. */
  overviewHints: [
    'Pick a module in the sidebar to see its runner pattern and API surface one at a time.',
    'Adding a module: implement run_prompt in Python, register in agents.json, then append an entry to HELP_MODULES in this file.',
  ],
}

/** Label for the right-hand detail header when a module is selected. */
export const HELP_DETAIL_LABELS = {
  agentKey: 'agent_key',
  pattern: 'How it runs',
  apiSurface: 'HTTP / UI',
  streaming: 'Streaming',
}

/** @type {HelpModuleEntry[]} */
export const HELP_MODULES = [
  {
    module: '01',
    title: 'Single Agent',
    agentKey: 'simple_litellm_agent',
    pattern:
      'One ADK Runner, sync run(), one LiteLLM-backed model; full reply when events finish.',
    apiSurface: 'POST /api/chat — blocking JSON response.',
    supportsStreaming: false,
  },
  {
    module: '02',
    title: 'Multi Agent',
    agentKey: 'mulit_agent',
    pattern: 'Two specialists on the same topic; results merged into one markdown answer.',
    apiSurface: 'POST /api/chat — one combined response.',
    supportsStreaming: false,
  },
  {
    module: '03',
    title: 'Orchestrator',
    agentKey: 'orchestrate_agent',
    pattern: 'Parses agent_type (explain / bullet / quiz), runs exactly one matching Runner.',
    apiSurface: 'POST /api/chat — routed specialist output.',
    supportsStreaming: false,
  },
  {
    module: '04',
    title: 'Streaming Agent',
    agentKey: 'streaming_agent',
    pattern:
      'Same model stack as 01, but run_async() yields ADK Events; chunks are sent as NDJSON lines.',
    apiSurface: 'POST /api/chat/stream — incremental deltas in the React UI.',
    supportsStreaming: true,
  },
  {
    module: '05',
    title: 'Weather Assistant (tools)',
    agentKey: 'advanced_agent',
    pattern:
      'ADK Agent with tools=[fetch_current_weather, celsius_to_fahrenheit_display]; Meteosource place_id; weather-only refusal for other topics.',
    apiSurface:
      'POST /api/chat or POST /api/chat/stream — incremental deltas in the React UI (set WEATHER_API_KEY in .env).',
    supportsStreaming: true,
  },
  {
    module: '06',
    title: 'Custom Agent (keyword router)',
    agentKey: 'custom_agent',
    pattern:
      'BaseAgent subclass: keyword routing to tech vs general LlmAgent; delegates with run_async(ctx) (no LLM router call).',
    apiSurface:
      'POST /api/chat or POST /api/chat/stream — incremental deltas in the React UI.',
    supportsStreaming: true,
  },
  {
    module: '07',
    title: 'Business Banking (multi-agent)',
    agentKey: 'multi_agent_banking',
    pattern:
      'SequentialAgent: deposit_agent → bill_agent → decision_agent; mock tools; output_key + state interpolation; get_overdraft_request returns demo_expected_decision (APPROVE/DENY) for CUST-1001/2002; stream emits \\x00AUDIT sentinels → NDJSON type audit; tool→agent fallback for attribution.',
    apiSurface:
      'POST /api/chat or POST /api/chat/stream — markdown reply + Pipeline Audit Trail (per-agent tools, JSON in/out). agents.json suggestions = Quick start chips. CLI: ./run_banking.sh [approve|deny|both].',
    supportsStreaming: true,
  },
  {
    module: '10',
    title: 'MCP Client (Redis banking)',
    agentKey: 'mcp_client',
    pattern:
      'Single LlmAgent with McpToolset over StdioConnectionParams. Connects to a Redis MCP server and uses customer-scoped Redis keys for business banking memory.',
    apiSurface:
      'POST /api/chat or POST /api/chat/stream — same chat UI flow as other registered modules. Requires Redis MCP server command configured in MODULE10_MCP_COMMAND/MODULE10_MCP_ARGS.',
    supportsStreaming: true,
  },
  {
    module: '11',
    title: 'MCP Server (OpenAPI explorer)',
    agentKey: 'mcp_server',
    pattern:
      'FastMCP server + ADK client pair. Loads OpenAPI specs at startup, indexes operations by operationId, resolves request/response schemas, and exposes search plus mock payload tools.',
    apiSurface:
      'POST /api/chat or POST /api/chat/stream — local stdio by default, or remote streamable HTTP with MODULE11_MCP_TRANSPORT=streamable-http and MODULE11_MCP_HTTP_URL.',
    supportsStreaming: true,
  },
  {
    module: '12',
    title: 'A2A CD Ladder Agent',
    agentKey: 'a2a_agent',
    pattern:
      'Local banking assistant delegates CD ladder planning to a remote fixed-income peer via Agent Card discovery and A2A task polling; falls back to a local mini-ladder when remote peer is unavailable.',
    apiSurface:
      'POST /api/chat through shared registry, or standalone Module 12 API at /chat. Specialist peer exposes /.well-known/agent-card and /a2a/tasks endpoints.',
    supportsStreaming: false,
  },
  {
    module: '13',
    title: 'Session Memory (retail deposit)',
    agentKey: 'retail_deposit_banking_agent',
    pattern:
      'Module 13 in-memory session use case: SequentialAgent (retail_intake_agent -> retail_risk_agent -> retail_offer_agent) plus session-level customer context reuse when follow-up prompts omit the customer ID.',
    apiSurface:
      'POST /api/chat via shared registry. Turn 1: send RET-3101 or RET-4420. Follow-up turns with the same session can omit customer ID.',
    supportsStreaming: false,
  },
]
