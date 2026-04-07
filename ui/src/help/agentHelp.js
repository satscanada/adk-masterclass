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
]
