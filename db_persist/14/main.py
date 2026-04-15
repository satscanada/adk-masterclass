"""Module 14 runner — same retail deposit pipeline as Module 13, SQLite-backed sessions."""

from __future__ import annotations

import argparse
import os
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from retail_deposit_banking_agent.agent import create_agent
from simple_litellm_agent.config import get_settings

CUSTOMER_ID_RE = re.compile(r"\bRET-\d{4}\b", re.IGNORECASE)
_SESSION_LAST_CUSTOMER: dict[tuple[str, str], str] = {}


def _default_db_url() -> str:
    db_path = Path(__file__).resolve().parent / "module14_sessions.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


def _session_db_url() -> str:
    return os.environ.get("MODULE14_DB_URL", _default_db_url()).strip()


@dataclass(frozen=True)
class RuntimeBundle:
    runner: Runner


@lru_cache(maxsize=1)
def build_runner() -> RuntimeBundle:
    settings = get_settings()
    session_service = DatabaseSessionService(_session_db_url())
    app_name = f"{settings.app_name}_module14_retail_deposit_db"
    runner = Runner(
        agent=create_agent(settings),
        app_name=app_name,
        session_service=session_service,
        auto_create_session=True,
    )
    return RuntimeBundle(runner=runner)


def reset_runtime() -> None:
    build_runner.cache_clear()


def _user_message(prompt: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=prompt)])


def _extract_customer_id(prompt: str) -> str | None:
    match = CUSTOMER_ID_RE.search(prompt)
    if not match:
        return None
    return match.group(0).upper()


def _resolve_customer_id(prompt: str, user_id: str, session_id: str) -> tuple[str, str]:
    key = (user_id, session_id)
    explicit_customer_id = _extract_customer_id(prompt)
    if explicit_customer_id:
        _SESSION_LAST_CUSTOMER[key] = explicit_customer_id
        return explicit_customer_id, "explicit"

    remembered_customer_id = _SESSION_LAST_CUSTOMER.get(key)
    if remembered_customer_id:
        return remembered_customer_id, "session_memory"

    raise ValueError(
        "Module 14 expects a retail customer ID like RET-3101 or RET-4420. "
        "For follow-up turns, reuse the same session_id (and optionally the same API process "
        "so in-process customer context matches Module 13)."
    )


def _normalize_prompt(prompt: str, customer_id: str, source: str) -> str:
    clean_prompt = prompt.strip()
    if source == "explicit":
        return clean_prompt
    return (
        f"{clean_prompt}\n\n"
        f"Use customer_id: {customer_id}\n"
        "(This customer_id comes from in-process session context for this session_id.)"
    )


def extract_final_text(events: Iterable) -> str:
    last_text = ""
    for event in events:
        if not event.content or not event.content.parts:
            continue
        text = "".join(part.text or "" for part in event.content.parts).strip()
        if text:
            last_text = text
    if not last_text:
        raise RuntimeError("Module 14 completed without producing text output.")
    return last_text


def _pipeline_banner(
    session_id: str,
    customer_id: str,
    customer_id_source: str,
    db_url: str,
) -> str:
    source_label = "prompt" if customer_id_source == "explicit" else "in-memory session"
    safe_db = db_url.split("@", 1)[-1] if "@" in db_url else db_url
    return (
        "**Module 14 pipeline:** `retail_intake_agent` -> `retail_risk_agent` -> `retail_offer_agent`\n\n"
        f"**Session mode:** `DatabaseSessionService` (`session_id={session_id}`)\n"
        f"**DB URL (sanitized):** `{safe_db}`\n"
        f"**Customer context:** `{customer_id}` (source: {source_label})\n\n"
        "---\n\n"
    )


def run_prompt(prompt: str, user_id: str = "demo-user", session_id: str | None = None) -> str:
    runtime = build_runner()
    resolved_session_id = session_id or str(uuid.uuid4())
    customer_id, customer_id_source = _resolve_customer_id(prompt, user_id, resolved_session_id)
    normalized_prompt = _normalize_prompt(prompt, customer_id, customer_id_source)
    db_url = _session_db_url()
    events = runtime.runner.run(
        user_id=user_id,
        session_id=resolved_session_id,
        new_message=_user_message(normalized_prompt),
    )
    return (
        _pipeline_banner(resolved_session_id, customer_id, customer_id_source, db_url)
        + extract_final_text(events)
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Module 14 retail deposit banking with DatabaseSessionService.",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="RET-3101",
        help="Retail customer ID (default: RET-3101). Try RET-4420 for review-required outcome.",
    )
    args = parser.parse_args()
    print(run_prompt(args.prompt))


if __name__ == "__main__":
    main()
