"""Module 14A runner — persistent spending coach on PostgreSQL."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from sqlalchemy.pool import NullPool

from simple_litellm_agent.config import get_settings

from .agent import create_agent

CUSTOMER_ID_RE = re.compile(r"\bCUST-\d{4}\b", re.IGNORECASE)
RESPONSE_RE = re.compile(r"\b(accepted|declined|not_now)\b", re.IGNORECASE)


def _session_db_url() -> str:
    return os.environ.get(
        "MODULE14A_DB_URL",
        "postgresql+asyncpg://postgres:postgres@127.0.0.1:6433/adk_sessions",
    ).strip()


def _session_db_schema() -> str:
    return os.environ.get("MODULE14A_DB_SCHEMA", "adk_module14a").strip()


def _session_scope_mode() -> str:
    """Session identity scope: customer (default) or user."""
    mode = os.environ.get("MODULE14A_SESSION_SCOPE", "customer").strip().lower()
    return mode if mode in {"customer", "user"} else "customer"


def _effective_user_id(customer_id: str, requested_user_id: str) -> str:
    """
    Build user_id used for ADK session keys.

    ADK DB sessions are keyed by (app_name, user_id, session_id). For this lesson we
    default to customer-scoped sessions so CLI and API runs can resume the same
    customer thread even when callers pass different user_id values.
    """
    if _session_scope_mode() == "customer":
        return f"customer::{customer_id.lower()}"
    return requested_user_id.strip() or "module14a-user"


@dataclass(frozen=True)
class RuntimeBundle:
    runner: Runner
    session_service: DatabaseSessionService
    app_name: str


@dataclass(frozen=True)
class PhaseTimings:
    """Wall-clock breakdown of a single run_prompt call (all values in ms)."""
    session_setup_ms: int
    pre_diagnostics_ms: int
    pipeline_ms: int          # runner.run() + full event consumption
    post_diagnostics_ms: int
    total_ms: int
    # Per-agent: first-event to last-event wall time while consuming the stream.
    # Key = ADK event author (agent name); value = elapsed ms.
    agent_timings: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeDiagnostics:
    sessions_for_effective_user: int
    state_keys: int
    spending_log_entries: int
    suggestion_history_entries: int
    latest_week: str | None
    latest_category: str | None
    latest_amount: float | None


@lru_cache(maxsize=1)
def build_runner() -> RuntimeBundle:
    settings = get_settings()
    app_name = f"{settings.app_name}_module14a_spending_coach"
    db_schema = _session_db_schema()
    # Postgres + asyncpg can raise "Future attached to a different loop" when pooled
    # connections are reused across separate event loops.
    # Runner.run(...) and the local asyncio.run(...) helper in this module use
    # different loops, so force loop-safe non-pooled behavior here.
    connect_args = (
        {"server_settings": {"search_path": db_schema}}
        if db_schema
        else {}
    )
    session_service = DatabaseSessionService(
        _session_db_url(),
        connect_args=connect_args,
        poolclass=NullPool,
        pool_pre_ping=False,
    )
    runner = Runner(
        agent=create_agent(settings),
        app_name=app_name,
        session_service=session_service,
        auto_create_session=False,
    )
    return RuntimeBundle(runner=runner, session_service=session_service, app_name=app_name)


def reset_runtime() -> None:
    build_runner.cache_clear()


def _extract_customer_id(prompt: str) -> str:
    match = CUSTOMER_ID_RE.search(prompt)
    if not match:
        raise ValueError(
            "Module 14A expects a business customer ID like CUST-3001, CUST-3002, or CUST-3003."
        )
    return match.group(0).upper()


def _extract_customer_response(prompt: str) -> str | None:
    match = RESPONSE_RE.search(prompt)
    return match.group(0).lower() if match else None


def _stable_session_id(customer_id: str) -> str:
    return f"spending-coach-{customer_id.lower()}"


def _seed_state_for_customer(customer_id: str) -> dict:
    seed = {
        "customer_id": customer_id,
        "spending_log": [],
        "suggestion_history": [],
    }
    if customer_id == "CUST-3003":
        seed["suggestion_history"] = [
            {
                "customer_id": customer_id,
                "category": "grocery",
                "response": "declined",
                "recorded_at": (datetime.now(UTC) - timedelta(days=10)).isoformat(),
            }
        ]
    return seed


def _user_message(prompt: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=prompt)])


def _normalize_prompt(customer_id: str, response: str | None) -> str:
    lines = [f"customer_id={customer_id}"]
    if response:
        lines.append(f"customer_response={response}")
    return "\n".join(lines)


def _normalize_prompt_with_optional_snapshot(
    customer_id: str,
    response: str | None,
    week: str | None,
    category: str | None,
    amount: float | None,
) -> str:
    lines = [f"customer_id={customer_id}"]
    if response:
        lines.append(f"customer_response={response}")
    if week:
        lines.append(f"week={week}")
    if category:
        lines.append(f"category={category}")
    if amount is not None:
        lines.append(f"amount={amount}")
    return "\n".join(lines)


async def _ensure_session(
    session_service: DatabaseSessionService,
    app_name: str,
    user_id: str,
    session_id: str,
    customer_id: str,
):
    session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if session:
        return session, False

    created = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state=_seed_state_for_customer(customer_id),
    )
    return created, True


def extract_final_text(events: Iterable) -> str:
    """Consume events and return the final normalised markdown text."""
    text, _ = _extract_text_with_timing(events)
    return text


def _extract_text_with_timing(events: Iterable) -> tuple[str, dict[str, int]]:
    """Consume events, return (normalised_text, per_agent_elapsed_ms).

    Per-agent timing is measured as the wall-clock span from the first event
    emitted by that agent to the last, captured while iterating the stream.
    An agent typically produces multiple events (one per LLM call + tool round-
    trip), so this reflects how long it held the pipeline open.
    """
    last_text = ""
    # Track first/last perf_counter timestamp per agent author.
    agent_first: dict[str, float] = {}
    agent_last: dict[str, float] = {}

    for event in events:
        now = time.perf_counter()
        author: str = getattr(event, "author", None) or ""
        if author and author not in {"user", ""}:
            if author not in agent_first:
                agent_first[author] = now
            agent_last[author] = now

        if not event.content or not event.content.parts:
            continue
        text = "".join(part.text or "" for part in event.content.parts).strip()
        if text:
            last_text = text

    if not last_text:
        raise RuntimeError("Module 14A completed without producing text output.")

    agent_timings = {
        name: max(1, round((agent_last[name] - agent_first[name]) * 1000))
        for name in agent_first
    }
    return _normalize_final_markdown(last_text), agent_timings


def _normalize_final_markdown(text: str) -> str:
    """
    Keep lesson output shape stable even when the LLM varies formatting.

    We expect:
    - ## Spending Coach Result
    - trend/suppression status
    - ### Coaching Message
    """
    normalized = text.strip()
    if "## Spending Coach Result" not in normalized:
        normalized = f"## Spending Coach Result\n\n{normalized}"

    if "### Coaching Message" in normalized:
        return normalized

    lines = [line.rstrip() for line in normalized.splitlines()]
    message_lines: list[str] = []
    for line in reversed(lines):
        if not line.strip():
            if message_lines:
                break
            continue
        if line.lstrip().startswith(("-", "*")):
            if message_lines:
                break
            continue
        if line.strip().startswith("#"):
            if message_lines:
                break
            continue
        message_lines.append(line.strip())
        if len(message_lines) >= 3:
            break

    message = " ".join(reversed(message_lines)).strip()
    if not message:
        message = "No coaching suggestion at this time. Keep logging additional weeks."
    else:
        # Remove the trailing free-form paragraph that we are promoting into
        # the explicit "### Coaching Message" section to avoid duplicated text.
        trimmed_lines = [line.rstrip() for line in normalized.splitlines()]
        while trimmed_lines and not trimmed_lines[-1].strip():
            trimmed_lines.pop()
        tail_len = len(message_lines)
        if tail_len > 0 and len(trimmed_lines) >= tail_len:
            tail = [line.strip() for line in trimmed_lines[-tail_len:]]
            if tail == list(reversed(message_lines)):
                trimmed_lines = trimmed_lines[:-tail_len]
                while trimmed_lines and not trimmed_lines[-1].strip():
                    trimmed_lines.pop()
                normalized = "\n".join(trimmed_lines).strip()

    return f"{normalized}\n\n### Coaching Message\n{message}"


async def _collect_runtime_diagnostics(
    session_service: DatabaseSessionService,
    app_name: str,
    user_id: str,
    session_id: str,
) -> RuntimeDiagnostics:
    sessions = await session_service.list_sessions(
        app_name=app_name,
        user_id=user_id,
    )
    session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    state = session.state if session else {}
    spending_log = state.get("spending_log", []) if isinstance(state, dict) else []
    suggestion_history = (
        state.get("suggestion_history", []) if isinstance(state, dict) else []
    )
    latest_week: str | None = None
    latest_category: str | None = None
    latest_amount: float | None = None
    if isinstance(spending_log, list) and spending_log:
        last = spending_log[-1]
        if isinstance(last, dict):
            latest_week = str(last.get("week")) if last.get("week") is not None else None
            latest_category = (
                str(last.get("category")) if last.get("category") is not None else None
            )
            raw_amount = last.get("amount")
            if isinstance(raw_amount, (int, float)):
                latest_amount = float(raw_amount)
            elif isinstance(raw_amount, str):
                try:
                    latest_amount = float(raw_amount)
                except ValueError:
                    latest_amount = None
    return RuntimeDiagnostics(
        sessions_for_effective_user=len(sessions.sessions),
        state_keys=len(state.keys()) if isinstance(state, dict) else 0,
        spending_log_entries=len(spending_log) if isinstance(spending_log, list) else 0,
        suggestion_history_entries=(
            len(suggestion_history) if isinstance(suggestion_history, list) else 0
        ),
        latest_week=latest_week,
        latest_category=latest_category,
        latest_amount=latest_amount,
    )


def _fmt_ms(ms: int) -> str:
    """Human-friendly millisecond label: <1s shows ms, >=1s shows s with one decimal."""
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms / 1000:.1f}s"


def _pipeline_banner(
    customer_id: str,
    requested_user_id: str,
    effective_user_id: str,
    session_id: str,
    created_new_session: bool,
    db_url: str,
    db_schema: str,
    requested_snapshot: str | None,
    customer_response: str | None,
    before_diagnostics: RuntimeDiagnostics | None,
    diagnostics: RuntimeDiagnostics | None,
    timings: PhaseTimings | None = None,
) -> str:
    safe_db = db_url.split("@", 1)[-1] if "@" in db_url else db_url
    session_mode = "created" if created_new_session else "resumed"
    diagnostics_block = ""
    if diagnostics is not None:
        log_delta = (
            diagnostics.spending_log_entries
            - before_diagnostics.spending_log_entries
            if before_diagnostics is not None
            else 0
        )
        history_delta = (
            diagnostics.suggestion_history_entries
            - before_diagnostics.suggestion_history_entries
            if before_diagnostics is not None
            else 0
        )
        latest_snapshot = "n/a"
        if diagnostics.latest_week and diagnostics.latest_category and diagnostics.latest_amount is not None:
            latest_snapshot = (
                f"{diagnostics.latest_week} / {diagnostics.latest_category} / "
                f"{diagnostics.latest_amount:.2f}"
            )
        diagnostics_block = (
            f"**Trace:** sessions_for_effective_user=`{diagnostics.sessions_for_effective_user}` · "
            f"state_keys=`{diagnostics.state_keys}` · "
            f"spending_log_entries=`{diagnostics.spending_log_entries}` · "
            f"suggestion_history_entries=`{diagnostics.suggestion_history_entries}`\n"
            f"**Run deltas:** spending_log_delta=`{log_delta}` · "
            f"suggestion_history_delta=`{history_delta}`\n"
            f"**Latest logged snapshot:** `{latest_snapshot}`\n"
        )

    timing_block = ""
    if timings is not None:
        agent_parts = " · ".join(
            f"`{name}`={_fmt_ms(ms)}"
            for name, ms in timings.agent_timings.items()
        )
        pipeline_detail = (
            f"{_fmt_ms(timings.pipeline_ms)}"
            + (f" ({agent_parts})" if agent_parts else "")
        )
        timing_block = (
            f"**Timing:** total=`{_fmt_ms(timings.total_ms)}` · "
            f"session_setup=`{_fmt_ms(timings.session_setup_ms)}` · "
            f"pre_diag=`{_fmt_ms(timings.pre_diagnostics_ms)}` · "
            f"pipeline={pipeline_detail} · "
            f"post_diag=`{_fmt_ms(timings.post_diagnostics_ms)}`\n"
        )

    return (
        "**Module 14A pipeline:** `spending_log_agent` -> `spending_coaching_agent`\n\n"
        f"**Persistence:** `DatabaseSessionService` (`{session_mode}` session)\n"
        f"**Database:** `{safe_db}`\n"
        f"**DB schema (search_path):** `{db_schema or 'default'}`\n"
        f"**Customer:** `{customer_id}`\n"
        f"**requested user_id:** `{requested_user_id}`\n"
        f"**effective user_id:** `{effective_user_id}` (`scope={_session_scope_mode()}`)\n"
        f"**session_id:** `{session_id}`\n\n"
        f"**Requested snapshot override:** `{requested_snapshot or 'none'}`\n"
        f"**Customer response:** `{customer_response or 'none'}`\n"
        f"{diagnostics_block}"
        f"{timing_block}"
        "---\n\n"
    )


_VALID_RESPONSES = {"accepted", "declined", "not_now"}


def run_prompt(
    prompt: str,
    user_id: str = "module14a-user",
    session_id: str | None = None,
    week: str | None = None,
    category: str | None = None,
    amount: float | None = None,
    customer_response: str | None = None,
) -> str:
    """Run a Module 14A spending-coach turn.

    customer_response — explicit suggestion reply ('accepted', 'declined', 'not_now').
                        When provided it takes precedence over any response keyword
                        embedded in the prompt string.  Pass it via --response on the
                        CLI or as the dedicated API field.
    """
    t_start = time.perf_counter()

    runtime = build_runner()
    customer_id = _extract_customer_id(prompt)
    # Explicit parameter wins; fall back to keyword extracted from the prompt string.
    if customer_response:
        norm = customer_response.strip().lower()
        if norm not in _VALID_RESPONSES:
            raise ValueError(
                f"customer_response must be one of: {', '.join(sorted(_VALID_RESPONSES))}. "
                f"Got: {customer_response!r}"
            )
        customer_response = norm
    else:
        customer_response = _extract_customer_response(prompt)
    resolved_session_id = session_id or _stable_session_id(customer_id)
    requested_user_id = user_id.strip() or "module14a-user"
    resolved_user_id = _effective_user_id(customer_id, requested_user_id)

    session, created_new_session = asyncio.run(
        _ensure_session(
            session_service=runtime.session_service,
            app_name=runtime.app_name,
            user_id=resolved_user_id,
            session_id=resolved_session_id,
            customer_id=customer_id,
        )
    )
    t_session = time.perf_counter()

    before_diagnostics: RuntimeDiagnostics | None = None
    try:
        before_diagnostics = asyncio.run(
            _collect_runtime_diagnostics(
                session_service=runtime.session_service,
                app_name=runtime.app_name,
                user_id=resolved_user_id,
                session_id=session.id,
            )
        )
    except Exception:
        before_diagnostics = None
    t_pre_diag = time.perf_counter()

    normalized_prompt = _normalize_prompt_with_optional_snapshot(
        customer_id=customer_id,
        response=customer_response,
        week=week,
        category=category,
        amount=amount,
    )
    events = runtime.runner.run(
        user_id=resolved_user_id,
        session_id=session.id,
        new_message=_user_message(normalized_prompt),
    )
    # Consume the full event stream before collecting post-run diagnostics.
    # ADK only flushes session.state to the DB as events are iterated; reading
    # diagnostics before this point always shows the pre-run state.
    final_text, agent_timings = _extract_text_with_timing(events)
    t_pipeline = time.perf_counter()

    diagnostics: RuntimeDiagnostics | None = None
    try:
        diagnostics = asyncio.run(
            _collect_runtime_diagnostics(
                session_service=runtime.session_service,
                app_name=runtime.app_name,
                user_id=resolved_user_id,
                session_id=session.id,
            )
        )
    except Exception:
        diagnostics = None
    t_post_diag = time.perf_counter()

    timings = PhaseTimings(
        session_setup_ms=round((t_session - t_start) * 1000),
        pre_diagnostics_ms=round((t_pre_diag - t_session) * 1000),
        pipeline_ms=round((t_pipeline - t_pre_diag) * 1000),
        post_diagnostics_ms=round((t_post_diag - t_pipeline) * 1000),
        total_ms=round((t_post_diag - t_start) * 1000),
        agent_timings=agent_timings,
    )

    return (
        _pipeline_banner(
            customer_id=customer_id,
            requested_user_id=requested_user_id,
            effective_user_id=resolved_user_id,
            session_id=session.id,
            created_new_session=created_new_session,
            db_url=_session_db_url(),
            db_schema=_session_db_schema(),
            requested_snapshot=(
                f"{week or '?'} / {category or '?'} / {amount}"
                if week or category or amount is not None
                else None
            ),
            customer_response=customer_response,
            before_diagnostics=before_diagnostics,
            diagnostics=diagnostics,
            timings=timings,
        )
        + final_text
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Module 14A spending coach with PostgreSQL-backed sessions.",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="CUST-3001",
        help="Customer ID prompt (default: CUST-3001). Optional response: declined/accepted/not_now.",
    )
    parser.add_argument(
        "--user-id",
        default="module14a-user",
        help="Stable user ID for session continuity (default: module14a-user).",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Optional explicit session ID. Defaults to spending-coach-<customer>.",
    )
    parser.add_argument(
        "--week",
        default=None,
        help="Optional custom week override for simulation (for example 2026-W20).",
    )
    parser.add_argument(
        "--category",
        default=None,
        help="Optional custom category override (for example dining, grocery, travel).",
    )
    parser.add_argument(
        "--amount",
        type=float,
        default=None,
        help="Optional custom amount override for simulation.",
    )
    parser.add_argument(
        "--response",
        choices=["accepted", "declined", "not_now"],
        default=None,
        metavar="RESPONSE",
        help=(
            "Customer response to a prior coaching suggestion. "
            "One of: accepted, declined, not_now."
        ),
    )
    args = parser.parse_args()
    print(
        run_prompt(
            args.prompt,
            user_id=args.user_id,
            session_id=args.session_id,
            week=args.week,
            category=args.category,
            amount=args.amount,
            customer_response=args.response,
        )
    )


if __name__ == "__main__":
    main()
