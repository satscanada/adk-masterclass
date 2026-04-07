import { useCallback, useEffect, useMemo, useState } from 'react'

import { HelpOverlay } from './help/HelpOverlay.jsx'

const API_BASE_URL = (import.meta.env.VITE_AGENT_API_BASE_URL || '/api').replace(/\/$/, '')
const DEFAULT_USER_ID = 'react-user'

function createSessionId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID()
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function CopyIcon({ className }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
    </svg>
  )
}

function CheckIcon({ className }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

function ChevronDownIcon({ className }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  )
}

function InfoCircleIcon({ className }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4" />
      <path d="M12 8h.01" />
    </svg>
  )
}

/** Renders `**bold**` as <strong>; keeps newlines via parent whitespace-pre-wrap. */
function renderBoldMarkdown(text) {
  const parts = text.split(/\*\*/)
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <strong key={i} className="font-semibold text-inherit">
        {part}
      </strong>
    ) : (
      part
    ),
  )
}

function MessageBubble({ role, content }) {
  const isUser = role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={[
          'max-w-3xl rounded-3xl px-4 py-3 text-sm leading-7 shadow-lg ring-1',
          isUser
            ? 'bg-blue-500 text-white ring-blue-300/50'
            : 'bg-slate-900/75 text-slate-100 ring-white/10',
        ].join(' ')}
      >
        <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-white/65">
          {isUser ? 'You' : 'Agent'}
        </p>
        <div className="whitespace-pre-wrap">{renderBoldMarkdown(content)}</div>
      </div>
    </div>
  )
}

function formatToolJson(obj) {
  if (obj == null || typeof obj !== 'object') {
    return String(obj)
  }
  try {
    return JSON.stringify(obj, null, 2)
  } catch {
    return String(obj)
  }
}

function AgentStep({ step, isLast }) {
  const isDone = step.status === 'done'

  return (
    <div className="relative pl-7">
      {!isLast && (
        <div className="absolute left-[9px] top-6 bottom-0 w-px bg-white/10" />
      )}
      <div
        className={[
          'absolute left-0 top-[5px] flex h-[19px] w-[19px] items-center justify-center rounded-full text-[10px] font-bold',
          isDone
            ? 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30'
            : 'bg-blue-500/20 text-blue-400 ring-1 ring-blue-500/30 animate-pulse',
        ].join(' ')}
      >
        {isDone ? '\u2713' : '\u2022'}
      </div>

      <div className="flex items-center gap-2 mb-1">
        <span className="text-[12px] font-semibold text-slate-200">{step.agent}</span>
        <span
          className={[
            'inline-block rounded-full px-2 py-[1px] text-[9px] font-semibold uppercase tracking-wider',
            isDone
              ? 'bg-emerald-500/15 text-emerald-300/90'
              : 'bg-blue-500/15 text-blue-300/90',
          ].join(' ')}
        >
          {isDone ? 'done' : 'running'}
        </span>
      </div>

      {step.tools.length > 0 && (
        <div className="mt-1 space-y-2 pb-3">
          {step.tools.map((tool, j) => (
            <div
              key={`${tool.name}-${j}`}
              className="rounded-xl border border-white/[0.06] bg-white/[0.03] px-3 py-2.5"
            >
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                <span className="text-[10px] text-amber-400/80">{'\u26A1'}</span>
                <code className="text-[11px] font-mono text-slate-200">{tool.name}</code>
                <span className="text-[9px] uppercase tracking-wider text-slate-500">tool</span>
              </div>
              <div className="mt-2 space-y-1.5">
                <div>
                  <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">
                    Input (arguments)
                  </p>
                  <pre className="mt-0.5 max-h-28 overflow-auto rounded-lg border border-white/[0.05] bg-black/25 px-2 py-1.5 font-mono text-[10px] leading-relaxed text-slate-300">
                    {formatToolJson(tool.input)}
                  </pre>
                </div>
                {tool.output && Object.keys(tool.output).length > 0 ? (
                  <div>
                    <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">
                      Output (tool return)
                    </p>
                    <pre className="mt-0.5 max-h-36 overflow-auto rounded-lg border border-emerald-500/15 bg-emerald-500/[0.06] px-2 py-1.5 font-mono text-[10px] leading-relaxed text-slate-200">
                      {formatToolJson(tool.output)}
                    </pre>
                  </div>
                ) : tool.status === 'pending' ? (
                  <p className="text-[10px] text-slate-500 italic">Waiting for tool result…</p>
                ) : (
                  <p className="text-[10px] text-slate-500">No summary fields for this tool.</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      {step.tools.length === 0 && <div className="pb-2" />}
    </div>
  )
}

function AuditTrail({ events, isStreaming }) {
  const [collapsed, setCollapsed] = useState(false)

  const agentSteps = useMemo(() => {
    const steps = []
    const indexByAgent = new Map()

    const ensureStep = (agentName) => {
      if (!agentName) {
        return null
      }
      let idx = indexByAgent.get(agentName)
      if (idx === undefined) {
        idx = steps.length
        indexByAgent.set(agentName, idx)
        steps.push({ agent: agentName, status: 'running', tools: [] })
      }
      return idx
    }

    for (const evt of events) {
      if (evt.event === 'agent_start') {
        ensureStep(evt.agent)
      } else if (evt.event === 'agent_end') {
        const idx = indexByAgent.get(evt.agent)
        if (idx !== undefined) {
          steps[idx].status = 'done'
        }
      } else if (evt.event === 'tool_call') {
        const idx = ensureStep(evt.agent)
        if (idx !== undefined) {
          steps[idx].tools.push({
            name: evt.tool,
            input: evt.input || {},
            output: null,
            status: 'pending',
          })
        }
      } else if (evt.event === 'tool_result') {
        const idx = indexByAgent.get(evt.agent)
        if (idx === undefined) {
          continue
        }
        const tools = steps[idx].tools
        for (let t = tools.length - 1; t >= 0; t -= 1) {
          if (tools[t].name === evt.tool && tools[t].status === 'pending') {
            tools[t].output = evt.output_summary || {}
            tools[t].status = 'done'
            break
          }
        }
      }
    }
    return steps
  }, [events])

  if (!agentSteps.length) return null

  const doneCount = agentSteps.filter((s) => s.status === 'done').length

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/60 shadow-lg backdrop-blur overflow-hidden">
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-white/[0.04]"
      >
        <div className="flex items-center gap-2.5">
          <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-violet-500/20 text-[11px] ring-1 ring-violet-500/25">
            {'\uD83D\uDD0D'}
          </span>
          <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            Pipeline Audit Trail
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isStreaming && doneCount < agentSteps.length ? (
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-400" />
          ) : null}
          <span className="text-[10px] font-medium tabular-nums text-slate-500">
            {doneCount}/{agentSteps.length} agents
          </span>
          <ChevronDownIcon
            className={`h-3.5 w-3.5 text-slate-500 transition-transform ${collapsed ? '-rotate-90' : ''}`}
          />
        </div>
      </button>

      {!collapsed && (
        <div className="border-t border-white/[0.06] px-4 py-3">
          {agentSteps.map((step, i) => (
            <AgentStep
              key={`${step.agent}-${i}`}
              step={step}
              isLast={i === agentSteps.length - 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function App() {
  const [agents, setAgents] = useState([])
  const [selectedKey, setSelectedKey] = useState('')
  const [messagesByAgent, setMessagesByAgent] = useState({})
  const [sessionsByAgent, setSessionsByAgent] = useState({})
  const [prompt, setPrompt] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [hintCopied, setHintCopied] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)

  const closeHelp = useCallback(() => setHelpOpen(false), [])

  useEffect(() => {
    function onGlobalKeyDown(event) {
      if (!event.ctrlKey || event.key.toLowerCase() !== 'h') {
        return
      }
      event.preventDefault()
      setHelpOpen(true)
    }
    window.addEventListener('keydown', onGlobalKeyDown)
    return () => window.removeEventListener('keydown', onGlobalKeyDown)
  }, [])

  useEffect(() => {
    async function fetchAgents() {
      setLoadError('')

      try {
        const response = await fetch(`${API_BASE_URL}/agents`)
        if (!response.ok) {
          throw new Error(`Failed to load agents (${response.status})`)
        }

        const payload = await response.json()
        console.log('[api] GET /agents response', payload)
        const nextAgents = (payload.agents || []).map((agent) => ({
          ...agent,
          supports_streaming: Boolean(agent.supports_streaming),
        }))
        setAgents(nextAgents)

        if (!nextAgents.length) {
          setLoadError('No agents were returned by the API.')
          return
        }

        setSelectedKey((currentKey) => currentKey || nextAgents[0].key)
        setSessionsByAgent((current) => {
          const next = { ...current }
          nextAgents.forEach((agent) => {
            if (!next[agent.key]) {
              next[agent.key] = createSessionId()
            }
          })
          return next
        })
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : 'Failed to load agents.')
      }
    }

    fetchAgents()
  }, [])

  useEffect(() => {
    setHintCopied(false)
  }, [selectedKey])

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.key === selectedKey) || null,
    [agents, selectedKey],
  )

  const activeMessages = messagesByAgent[selectedKey] || []
  const activeSessionId = sessionsByAgent[selectedKey] || ''

  async function handleSubmit(event) {
    event.preventDefault()

    const cleanPrompt = prompt.trim()
    if (!cleanPrompt || !selectedAgent || isLoading) {
      return
    }

    const sessionId = activeSessionId || createSessionId()
    const userMessage = { role: 'user', content: cleanPrompt }
    const useStream = Boolean(selectedAgent.supports_streaming)

    setPrompt('')
    setIsLoading(true)
    setLoadError('')
    setMessagesByAgent((current) => ({
      ...current,
      [selectedKey]: [
        ...(current[selectedKey] || []),
        userMessage,
        ...(useStream ? [{ role: 'assistant', content: '' }] : []),
      ],
    }))
    setSessionsByAgent((current) => ({
      ...current,
      [selectedKey]: sessionId,
    }))

    try {
      if (useStream) {
        const response = await fetch(`${API_BASE_URL}/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            agent_key: selectedKey,
            prompt: cleanPrompt,
            user_id: DEFAULT_USER_ID,
            session_id: sessionId,
          }),
        })

        if (!response.ok) {
          const payload = await response.json().catch(() => ({}))
          console.log('[api] POST /chat/stream error response', response.status, payload)
          const detail = payload.detail
          const detailStr =
            typeof detail === 'string'
              ? detail
              : Array.isArray(detail)
                ? detail.map((d) => d.msg || d).join(' ')
                : JSON.stringify(detail || payload)
          throw new Error(detailStr || `Request failed (${response.status})`)
        }

        console.log('[api] POST /chat/stream response', response.status, response.statusText)

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        let streamSessionId = sessionId

        while (true) {
          const { done, value } = await reader.read()
          if (done) {
            break
          }
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''
          for (const line of lines) {
            if (!line.trim()) {
              continue
            }
            const obj = JSON.parse(line)
            console.log('[api] POST /chat/stream chunk', obj)
            if (obj.type === 'audit') {
              setMessagesByAgent((current) => {
                const msgs = [...(current[selectedKey] || [])]
                const last = msgs.length - 1
                if (last >= 0 && msgs[last].role === 'assistant') {
                  msgs[last] = {
                    ...msgs[last],
                    audit: [...(msgs[last].audit || []), obj],
                  }
                }
                return { ...current, [selectedKey]: msgs }
              })
            } else if (obj.type === 'delta' && obj.text) {
              setMessagesByAgent((current) => {
                const msgs = [...(current[selectedKey] || [])]
                const last = msgs.length - 1
                if (last >= 0 && msgs[last].role === 'assistant') {
                  msgs[last] = {
                    ...msgs[last],
                    content: msgs[last].content + obj.text,
                  }
                }
                return { ...current, [selectedKey]: msgs }
              })
            } else if (obj.type === 'done' && obj.session_id) {
              streamSessionId = obj.session_id
            } else if (obj.type === 'error') {
              throw new Error(obj.detail || 'Stream error')
            }
          }
        }

        setSessionsByAgent((current) => ({
          ...current,
          [selectedKey]: streamSessionId,
        }))
      } else {
        const response = await fetch(`${API_BASE_URL}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            agent_key: selectedKey,
            prompt: cleanPrompt,
            user_id: DEFAULT_USER_ID,
            session_id: sessionId,
          }),
        })

        const payload = await response.json()
        console.log('[api] POST /chat response', response.status, payload)
        if (!response.ok) {
          throw new Error(payload.detail || `Request failed (${response.status})`)
        }

        setMessagesByAgent((current) => ({
          ...current,
          [selectedKey]: [
            ...(current[selectedKey] || []),
            { role: 'assistant', content: payload.response },
          ],
        }))
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Request failed.'
      setLoadError(message)
      setMessagesByAgent((current) => {
        const existing = current[selectedKey] || []
        const last = existing[existing.length - 1]
        if (useStream && last && last.role === 'assistant') {
          return {
            ...current,
            [selectedKey]: [
              ...existing.slice(0, -1),
              { role: 'assistant', content: `Error: ${message}` },
            ],
          }
        }
        return {
          ...current,
          [selectedKey]: [
            ...existing,
            { role: 'assistant', content: `Error: ${message}` },
          ],
        }
      })
    } finally {
      setIsLoading(false)
    }
  }

  function startNewConversation() {
    if (!selectedKey) {
      return
    }

    setMessagesByAgent((current) => ({
      ...current,
      [selectedKey]: [],
    }))
    setSessionsByAgent((current) => ({
      ...current,
      [selectedKey]: createSessionId(),
    }))
    setLoadError('')
  }

  const promptHintText = selectedAgent?.prompt_hint || 'Ask a normal question.'

  async function copyPromptHint() {
    const text = promptHintText
    try {
      await navigator.clipboard.writeText(text)
      setHintCopied(true)
      window.setTimeout(() => setHintCopied(false), 2000)
    } catch {
      setLoadError('Could not copy prompt hint to the clipboard.')
    }
  }

  return (
    <div className="min-h-screen bg-transparent px-4 py-6 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-7xl flex-col gap-6 lg:flex-row">
        <aside className="w-full rounded-3xl border border-white/10 bg-slate-950/70 p-5 shadow-2xl backdrop-blur lg:max-w-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-blue-200/70">
            ADK Learning Project
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white">
            Agent Chat UI
          </h1>
          <p className="mt-3 text-sm leading-7 text-slate-300">
            This React client talks to the Python API instead of importing the agents directly.
          </p>

          <div className="mt-6">
            <label className="block text-sm font-medium text-slate-200" htmlFor="agent-select">
              Choose an agent
            </label>
            <div className="relative mt-2">
              <select
                id="agent-select"
                className="w-full cursor-pointer appearance-none rounded-2xl border border-white/10 bg-slate-900/80 py-3 pl-4 pr-11 text-sm text-white shadow-inner outline-none transition hover:border-white/15 focus:border-blue-400/45 focus:ring-2 focus:ring-blue-500/25"
                value={selectedKey}
                onChange={(event) => setSelectedKey(event.target.value)}
              >
                {agents.map((agent) => (
                  <option key={agent.key} value={agent.key}>
                    {agent.title}
                  </option>
                ))}
              </select>
              <span
                className="pointer-events-none absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-r-2xl border-l border-white/10 bg-slate-800/50 text-slate-400"
                aria-hidden
              >
                <ChevronDownIcon className="h-4 w-4 opacity-90" />
              </span>
            </div>
          </div>

          {selectedAgent ? (
            <div className="mt-6 space-y-4">
              <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                  Agent details
                </p>
                <p className="mt-1.5 text-[11px] leading-5 text-slate-200">
                  {selectedAgent.description}
                </p>
                {selectedAgent.supports_streaming ? (
                  <p className="mt-1.5 text-[11px] leading-5 font-medium text-emerald-200/90">
                    Streaming: replies use{' '}
                    <code className="rounded bg-white/10 px-1 text-[10px]">POST /api/chat/stream</code>{' '}
                    (NDJSON chunks).
                  </p>
                ) : null}
              </div>

              <div className="rounded-xl border border-blue-400/20 bg-blue-500/10 px-3 py-2.5">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-blue-200/75">
                    Prompt hint
                  </p>
                  <button
                    type="button"
                    onClick={copyPromptHint}
                    title={hintCopied ? 'Copied' : 'Copy prompt hint'}
                    className="shrink-0 rounded p-1 text-blue-200/55 transition hover:bg-white/10 hover:text-blue-100/90"
                    aria-label={hintCopied ? 'Copied to clipboard' : 'Copy prompt hint to clipboard'}
                  >
                    {hintCopied ? (
                      <CheckIcon className="h-3.5 w-3.5 text-emerald-400/85" />
                    ) : (
                      <CopyIcon className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>
                <pre className="mt-1.5 whitespace-pre-wrap text-[11px] leading-5 text-blue-50/95">
                  {promptHintText}
                </pre>
              </div>

              <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-4 text-xs text-slate-400">
                <p>{`agent_key = ${selectedKey}`}</p>
                <p className="mt-2 break-all">{`session_id = ${activeSessionId || 'pending'}`}</p>
              </div>
            </div>
          ) : null}

          <div className="mt-6 flex gap-2">
            <button
              type="button"
              className="min-h-[48px] flex-1 rounded-2xl bg-blue-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:bg-blue-900"
              onClick={startNewConversation}
              disabled={!selectedKey || isLoading}
            >
              New conversation
            </button>
            <button
              type="button"
              className="flex min-h-[48px] min-w-[48px] shrink-0 items-center justify-center rounded-2xl border border-white/15 bg-slate-800/90 text-slate-200 transition hover:border-white/25 hover:bg-slate-700/90 disabled:cursor-not-allowed disabled:opacity-50"
              onClick={() => setHelpOpen(true)}
              disabled={isLoading}
              title="Help — modules and API (Ctrl+H)"
              aria-keyshortcuts="Control+H"
              aria-label="Open help"
              aria-expanded={helpOpen}
              aria-haspopup="dialog"
            >
              <InfoCircleIcon className="h-5 w-5" />
            </button>
          </div>
        </aside>

        <main className="flex min-h-[70vh] flex-1 flex-col rounded-3xl border border-white/10 bg-slate-950/55 shadow-2xl backdrop-blur">
          <div className="flex min-h-0 flex-nowrap items-center gap-3 border-b border-white/10 px-4 py-2.5 sm:px-6">
            <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Conversation
            </span>
            <h2 className="min-w-0 flex-1 truncate text-lg font-semibold leading-tight text-white sm:text-xl">
              {selectedAgent ? selectedAgent.title : 'Loading agents...'}
            </h2>
            <p className="shrink-0 text-xs text-slate-400">
              API base:{' '}
              <code className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[11px] text-slate-200">
                {API_BASE_URL}
              </code>
            </p>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
            {activeMessages.length ? (
              activeMessages.map((message, index) => (
                <div key={`msg-${index}`} className="space-y-3">
                  {message.audit?.length ? (
                    <AuditTrail events={message.audit} isStreaming={isLoading} />
                  ) : null}
                  <MessageBubble role={message.role} content={message.content} />
                </div>
              ))
            ) : (
              <div className="space-y-4">
                <div className="rounded-3xl border border-dashed border-white/15 bg-white/5 p-5 text-sm leading-7 text-slate-300">
                  Start the conversation below. The selected agent keeps its own session id and chat
                  history.
                </div>

                {selectedAgent?.suggestions?.length ? (
                  <div className="space-y-2.5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Quick start
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {selectedAgent.suggestions.map((suggestion) => (
                        <button
                          key={suggestion.prompt}
                          type="button"
                          disabled={isLoading}
                          className="group inline-flex items-center gap-2 rounded-2xl border border-blue-400/20 bg-blue-500/10 px-4 py-2.5 text-sm font-medium text-blue-100 shadow-sm transition hover:border-blue-400/40 hover:bg-blue-500/20 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
                          onClick={() => {
                            setPrompt(suggestion.prompt)
                            setTimeout(() => {
                              const form = document.querySelector('form')
                              if (form) form.requestSubmit()
                            }, 0)
                          }}
                        >
                          <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-500/25 text-[11px] font-bold text-blue-200/80 transition group-hover:bg-blue-500/40">
                            &#x2192;
                          </span>
                          {suggestion.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}

            {isLoading ? (
              <div className="inline-flex items-center rounded-full bg-white/10 px-4 py-2 text-sm text-slate-200">
                {selectedAgent?.supports_streaming
                  ? `Streaming from ${selectedAgent?.title || 'agent'}...`
                  : `Waiting for ${selectedAgent?.title || 'agent'}...`}
              </div>
            ) : null}

            {loadError ? (
              <div className="rounded-2xl border border-amber-300/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
                {loadError}
              </div>
            ) : null}
          </div>

          <form className="border-t border-white/10 p-4 sm:p-6" onSubmit={handleSubmit}>
            <div className="rounded-3xl border border-white/10 bg-slate-900/85 p-3 shadow-lg">
              <textarea
                className="min-h-32 w-full resize-none rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3 text-sm leading-7 text-white outline-none placeholder:text-slate-500"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key !== 'Enter' || !event.ctrlKey) {
                    return
                  }
                  event.preventDefault()
                  event.currentTarget.form?.requestSubmit()
                }}
                placeholder={promptHintText}
                disabled={!selectedAgent || isLoading}
              />
              <div className="mt-3 flex items-center justify-between gap-3">
                <p className="text-xs text-slate-400">
                  Talks to{' '}
                  <code className="rounded bg-white/5 px-1.5 py-0.5">
                    {`${API_BASE_URL}/${selectedAgent?.supports_streaming ? 'chat/stream' : 'chat'}`}
                  </code>
                </p>
                <button
                  type="submit"
                  className="rounded-2xl bg-blue-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:bg-blue-900"
                  disabled={!selectedAgent || isLoading || !prompt.trim()}
                >
                  {isLoading ? 'Sending...' : 'Send'}
                </button>
              </div>
            </div>
          </form>
        </main>
      </div>

      <HelpOverlay open={helpOpen} onClose={closeHelp} />
    </div>
  )
}

export default App
