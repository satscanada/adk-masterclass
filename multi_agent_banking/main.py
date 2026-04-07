"""Module 07: runner for the multi-agent banking overdraft pipeline.

Exposes the same contract as earlier modules:
  - run_prompt(prompt, user_id, session_id) -> str       (blocking, for POST /api/chat)
  - stream_prompt(prompt, user_id, session_id) -> async   (NDJSON, for POST /api/chat/stream)

Audit trail: stream_prompt emits sentinel-prefixed strings (\x00AUDIT:{json})
for agent transitions, tool calls, and tool results. api_app.py detects these
and converts them to {"type":"audit",...} NDJSON events for the React UI.
"""

from __future__ import annotations

import argparse
import asyncio
import json as _json
import logging
import uuid
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from simple_litellm_agent.config import get_settings

from .agent import create_agent

logger = logging.getLogger(__name__)

AUDIT_PREFIX = "\x00AUDIT:"
# SequentialAgent shell — not a leaf LlmAgent; skip as the "current" agent for tools.
_PIPELINE_ROOT = "banking_overdraft_pipeline"

# When event.author/branch are missing (some streams), attribute tools by name.
_TOOL_TO_AGENT: dict[str, str] = {
    "get_monthly_deposits": "deposit_agent",
    "get_balance_movement": "deposit_agent",
    "get_completed_bills": "bill_agent",
    "get_upcoming_bills": "bill_agent",
    "get_overdraft_request": "decision_agent",
}


def _agent_for_tool(tool_name: str) -> str | None:
    return _TOOL_TO_AGENT.get(tool_name)


def _effective_agent_name(event: Any, current: str | None) -> str | None:
    """Resolve which LlmAgent owns this event.

    Tool result events often use content role 'user' with author 'user'; branch
    carries the real leaf agent (e.g. banking_overdraft_pipeline.deposit_agent).
    """
    branch = getattr(event, "branch", None) or ""
    if branch:
        parts = [p for p in branch.split(".") if p.strip()]
        if len(parts) >= 2:
            return parts[-1]
        if len(parts) == 1 and parts[0] != _PIPELINE_ROOT:
            return parts[0]
    author = getattr(event, "author", None)
    if author and author not in ("user", "model"):
        if author == _PIPELINE_ROOT:
            return current
        return author
    return current


def _audit(payload: dict) -> str:
    return AUDIT_PREFIX + _json.dumps(payload, default=str)


def _safe_dict(obj: Any) -> dict:
    if isinstance(obj, dict):
        return obj
    try:
        return dict(obj)
    except (TypeError, ValueError):
        return {}


_TOOL_SUMMARY_FIELDS: dict[str, tuple[str, ...]] = {
    "get_monthly_deposits": ("customer_name", "deposit_count", "total_deposits", "average_deposit"),
    "get_balance_movement": ("customer_name", "current_balance", "min_balance", "max_balance", "average_balance"),
    "get_completed_bills": ("customer_name", "bill_count", "total_paid"),
    "get_upcoming_bills": ("customer_name", "bill_count", "total_upcoming"),
    "get_overdraft_request": (
        "customer_name",
        "account_number",
        "current_balance",
        "overdraft_limit_requested",
        "demo_expected_decision",
    ),
}


def _tool_output_summary(tool_name: str, raw_response: Any) -> dict:
    data = _safe_dict(raw_response)
    keys = _TOOL_SUMMARY_FIELDS.get(tool_name, ())
    return {k: data[k] for k in keys if k in data}


@dataclass(frozen=True)
class RuntimeBundle:
    runner: Runner


@lru_cache(maxsize=1)
def build_runner() -> RuntimeBundle:
    settings = get_settings()
    session_service = InMemorySessionService()
    app_name = f"{settings.app_name}_module07_banking"
    runner = Runner(
        agent=create_agent(settings),
        app_name=app_name,
        session_service=session_service,
        auto_create_session=True,
    )
    return RuntimeBundle(runner=runner)


def reset_runtime() -> None:
    build_runner.cache_clear()


def extract_final_text(events: Iterable) -> str:
    last_text = ""
    for event in events:
        if event.content and event.content.parts:
            text = "".join(part.text or "" for part in event.content.parts).strip()
            if text:
                last_text = text
    if not last_text:
        raise RuntimeError("The banking pipeline completed without producing text output.")
    return last_text


def _user_message(prompt: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=prompt)])


def _pipeline_banner() -> str:
    return (
        "**Pipeline:** `deposit_agent` → `bill_agent` → `decision_agent`\n\n"
        "---\n\n"
    )


def run_prompt(prompt: str, user_id: str = "demo-user", session_id: str | None = None) -> str:
    runtime = build_runner()
    resolved_session_id = session_id or str(uuid.uuid4())
    message = _user_message(prompt)
    events = list(runtime.runner.run(
        user_id=user_id,
        session_id=resolved_session_id,
        new_message=message,
    ))

    parts: list[str] = [_pipeline_banner()]
    for event in events:
        if getattr(event, "author", None) == "user":
            continue
        if not event.content or not event.content.parts:
            continue
        text = "".join(p.text or "" for p in event.content.parts).strip()
        if text:
            parts.append(text)

    if len(parts) == 1:
        parts.append(extract_final_text(events))

    return "\n\n".join(parts)


async def stream_prompt(
    prompt: str,
    user_id: str = "demo-user",
    session_id: str | None = None,
) -> AsyncIterator[str]:
    """Yield text chunks and audit sentinels from the SequentialAgent pipeline."""
    runtime = build_runner()
    resolved_session_id = session_id or str(uuid.uuid4())
    message = _user_message(prompt)

    yield _pipeline_banner()

    accumulated: list = []
    yielded_any = False
    current_agent: str | None = None

    async for event in runtime.runner.run_async(
        user_id=user_id,
        session_id=resolved_session_id,
        new_message=message,
    ):
        accumulated.append(event)

        if not event.content or not event.content.parts:
            continue

        effective = _effective_agent_name(event, current_agent)

        if effective and effective != current_agent:
            if current_agent:
                yield _audit({"event": "agent_end", "agent": current_agent})
            current_agent = effective
            yield _audit({"event": "agent_start", "agent": current_agent})

        acting = effective or current_agent

        for part in event.content.parts:
            fc = getattr(part, "function_call", None)
            if fc:
                tool_name = getattr(fc, "name", "unknown") or "unknown"
                tool_agent = acting or _agent_for_tool(tool_name)
                if tool_agent:
                    args = _safe_dict(getattr(fc, "args", None))
                    yield _audit({
                        "event": "tool_call",
                        "agent": tool_agent,
                        "tool": tool_name,
                        "input": args,
                    })
                continue

            fr = getattr(part, "function_response", None)
            if fr:
                tool_name = getattr(fr, "name", "unknown") or "unknown"
                tool_agent = acting or _agent_for_tool(tool_name)
                if tool_agent:
                    raw = getattr(fr, "response", None)
                    yield _audit({
                        "event": "tool_result",
                        "agent": tool_agent,
                        "tool": tool_name,
                        "output_summary": _tool_output_summary(tool_name, raw),
                    })
                continue

            chunk = getattr(part, "text", None) or ""
            if chunk:
                yielded_any = True
                yield chunk

    if current_agent:
        yield _audit({"event": "agent_end", "agent": current_agent})

    if yielded_any:
        return

    try:
        final = extract_final_text(accumulated)
    except RuntimeError as exc:
        logger.warning("stream_prompt: no streamed chunks and no final text: %s", exc)
        return
    if final:
        yield final


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Module 07 multi-agent banking overdraft pipeline.",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="CUST-1001",
        help="Customer ID to evaluate (default: CUST-1001). Try CUST-2002 for a weaker profile.",
    )
    args = parser.parse_args()

    async def _run() -> None:
        print("Banking Pipeline: ", end="", flush=True)
        async for piece in stream_prompt(args.prompt):
            if piece.startswith(AUDIT_PREFIX):
                audit = _json.loads(piece[len(AUDIT_PREFIX):])
                evt = audit.get("event", "")
                agent = audit.get("agent", "")
                if evt == "agent_start":
                    print(f"\n  [{agent}] started", flush=True)
                elif evt == "agent_end":
                    print(f"  [{agent}] done", flush=True)
                elif evt == "tool_call":
                    print(f"    -> {audit.get('tool', '?')}({audit.get('input', {})})", flush=True)
                elif evt == "tool_result":
                    print(f"    <- {audit.get('tool', '?')}: {audit.get('output_summary', {})}", flush=True)
            else:
                print(piece, end="", flush=True)
        print()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
