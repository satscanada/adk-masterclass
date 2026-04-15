"""Module 14A runner — persistent spending coach on PostgreSQL."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
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
    last_text = ""
    for event in events:
        if not event.content or not event.content.parts:
            continue
        text = "".join(part.text or "" for part in event.content.parts).strip()
        if text:
            last_text = text
    if not last_text:
        raise RuntimeError("Module 14A completed without producing text output.")
    return last_text


def _pipeline_banner(
    customer_id: str,
    requested_user_id: str,
    effective_user_id: str,
    session_id: str,
    created_new_session: bool,
    db_url: str,
    db_schema: str,
) -> str:
    safe_db = db_url.split("@", 1)[-1] if "@" in db_url else db_url
    session_mode = "created" if created_new_session else "resumed"
    return (
        "**Module 14A pipeline:** `spending_log_agent` -> `spending_coaching_agent`\n\n"
        f"**Persistence:** `DatabaseSessionService` (`{session_mode}` session)\n"
        f"**Database:** `{safe_db}`\n"
        f"**DB schema (search_path):** `{db_schema or 'default'}`\n"
        f"**Customer:** `{customer_id}`\n"
        f"**requested user_id:** `{requested_user_id}`\n"
        f"**effective user_id:** `{effective_user_id}` (`scope={_session_scope_mode()}`)\n"
        f"**session_id:** `{session_id}`\n\n"
        "---\n\n"
    )


def run_prompt(prompt: str, user_id: str = "module14a-user", session_id: str | None = None) -> str:
    runtime = build_runner()
    customer_id = _extract_customer_id(prompt)
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
    normalized_prompt = _normalize_prompt(customer_id, customer_response)
    events = runtime.runner.run(
        user_id=resolved_user_id,
        session_id=session.id,
        new_message=_user_message(normalized_prompt),
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
        )
        + extract_final_text(events)
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
    args = parser.parse_args()
    print(run_prompt(args.prompt, user_id=args.user_id, session_id=args.session_id))


if __name__ == "__main__":
    main()
