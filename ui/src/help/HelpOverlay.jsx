import { useEffect, useMemo, useState } from 'react'

import { HELP_DETAIL_LABELS, HELP_META, HELP_MODULES, HELP_NAV } from './agentHelp.js'

export function HelpOverlay({ open, onClose }) {
  const [activeId, setActiveId] = useState(HELP_NAV.overviewId)

  useEffect(() => {
    if (open) {
      setActiveId(HELP_NAV.overviewId)
    }
  }, [open])

  const activeModule = useMemo(
    () => HELP_MODULES.find((m) => m.agentKey === activeId) ?? null,
    [activeId],
  )

  useEffect(() => {
    if (!open) {
      return
    }
    function onKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  useEffect(() => {
    if (!open) {
      return
    }
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [open])

  if (!open) {
    return null
  }

  const navButtonClass = (isActive) =>
    [
      'w-full rounded-lg px-3 py-2 text-left text-xs transition sm:text-[13px]',
      isActive
        ? 'bg-blue-500/20 text-white ring-1 ring-blue-400/40'
        : 'text-slate-400 hover:bg-white/5 hover:text-slate-200',
    ].join(' ')

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/65 p-3 backdrop-blur-sm sm:p-4"
      role="presentation"
      onClick={onClose}
    >
      <article
        role="dialog"
        aria-modal="true"
        aria-labelledby="help-overlay-title"
        className="flex max-h-[min(92vh,760px)] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-white/15 bg-gradient-to-b from-slate-900 to-slate-950 shadow-2xl ring-1 ring-white/10"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex shrink-0 items-start justify-between gap-3 border-b border-white/10 px-4 py-3 sm:px-5 sm:py-4">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-blue-300/80">{HELP_META.eyebrow}</p>
            <h2 id="help-overlay-title" className="mt-1 text-lg font-semibold tracking-tight text-white sm:text-xl">
              {HELP_META.title}
            </h2>
            <p className="mt-1 text-[10px] text-slate-500 sm:text-[11px]">One module per view — use the sidebar to switch.</p>
          </div>
          <button
            type="button"
            className="shrink-0 rounded-lg border border-white/15 bg-white/5 px-2.5 py-1 text-sm text-slate-300 transition hover:bg-white/10"
            onClick={onClose}
            aria-label="Close help"
          >
            Esc
          </button>
        </header>

        <div className="flex min-h-0 flex-1 flex-col sm:flex-row">
          <nav
            className="flex shrink-0 flex-row gap-1 overflow-x-auto border-b border-white/10 px-2 py-2 sm:w-[13.5rem] sm:flex-col sm:overflow-x-visible sm:border-b-0 sm:border-r sm:px-2 sm:py-3"
            aria-label="Help sections"
          >
            <button
              type="button"
              className={navButtonClass(activeId === HELP_NAV.overviewId)}
              onClick={() => setActiveId(HELP_NAV.overviewId)}
              aria-current={activeId === HELP_NAV.overviewId ? 'true' : undefined}
            >
              <span className="font-mono text-[10px] text-slate-500">—</span>{' '}
              <span className="font-medium">{HELP_META.overviewNavLabel}</span>
            </button>
            {HELP_MODULES.map((row) => (
              <button
                key={row.agentKey}
                type="button"
                className={navButtonClass(activeId === row.agentKey)}
                onClick={() => setActiveId(row.agentKey)}
                aria-current={activeId === row.agentKey ? 'true' : undefined}
              >
                <span className="font-mono text-[10px] text-blue-400/90">{row.module}</span>{' '}
                <span className="font-medium">{row.title}</span>
              </button>
            ))}
          </nav>

          <div className="min-h-[min(50vh,420px)] min-w-0 flex-1 overflow-y-auto px-4 py-4 sm:min-h-0 sm:px-6 sm:py-5">
            {activeId === HELP_NAV.overviewId ? (
              <div className="space-y-4">
                <p className="text-xs leading-relaxed text-slate-400">
                  {HELP_META.introBeforeAgentsFile}
                  <code className="rounded bg-white/10 px-1 py-0.5 font-mono text-[10px]">agents.json</code>
                  {HELP_META.introAfterAgentsFile}
                </p>
                <ul className="list-inside list-disc space-y-2 text-[11px] leading-relaxed text-slate-400">
                  {HELP_META.overviewHints.map((line, index) => (
                    <li key={index}>{line}</li>
                  ))}
                </ul>
              </div>
            ) : activeModule ? (
              <div className="space-y-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-blue-400/90">Module {activeModule.module}</span>
                    {activeModule.supportsStreaming ? (
                      <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-emerald-300/90">
                        {HELP_DETAIL_LABELS.streaming}
                      </span>
                    ) : null}
                  </div>
                  <h3 className="mt-2 text-base font-semibold text-white sm:text-lg">{activeModule.title}</h3>
                  <p className="mt-1 font-mono text-[11px] text-slate-500">
                    <span className="text-slate-600">{HELP_DETAIL_LABELS.agentKey}: </span>
                    {activeModule.agentKey}
                  </p>
                </div>

                <section>
                  <h4 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                    {HELP_DETAIL_LABELS.pattern}
                  </h4>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-300">{activeModule.pattern}</p>
                </section>

                <section>
                  <h4 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                    {HELP_DETAIL_LABELS.apiSurface}
                  </h4>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{activeModule.apiSurface}</p>
                </section>
              </div>
            ) : null}
          </div>
        </div>

        <footer className="shrink-0 border-t border-white/10 px-4 py-2.5 text-center text-[10px] leading-relaxed text-slate-500 sm:px-5">
          Open from chat:{' '}
          <kbd className="rounded border border-white/15 bg-white/5 px-1.5 py-0.5 font-mono text-slate-400">Ctrl</kbd>
          +
          <kbd className="rounded border border-white/15 bg-white/5 px-1.5 py-0.5 font-mono text-slate-400">H</kbd>
          {' · '}
          Full reference: <code className="font-mono text-slate-400">AGENT_HELP.md</code>
          {' · '}
          <kbd className="rounded border border-white/15 bg-white/5 px-1.5 py-0.5 font-mono text-slate-400">Escape</kbd> or outside
          to close
        </footer>
      </article>
    </div>
  )
}
