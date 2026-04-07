from __future__ import annotations

import argparse
import re
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from simple_litellm_agent.config import get_settings

from .agent import (
    SUPPORTED_AGENT_TYPES,
    create_bullet_agent,
    create_explain_agent,
    create_quiz_agent,
)


@dataclass(frozen=True)
class RuntimeBundle:
    runners_by_type: dict[str, Runner]


@lru_cache(maxsize=1)
def build_runtimes() -> RuntimeBundle:
    settings = get_settings()
    session_service = InMemorySessionService()

    runners_by_type = {
        "explain": Runner(
            agent=create_explain_agent(settings),
            app_name=f"{settings.app_name}_orchestrate_explain",
            session_service=session_service,
            auto_create_session=True,
        ),
        "bullet": Runner(
            agent=create_bullet_agent(settings),
            app_name=f"{settings.app_name}_orchestrate_bullet",
            session_service=session_service,
            auto_create_session=True,
        ),
        "quiz": Runner(
            agent=create_quiz_agent(settings),
            app_name=f"{settings.app_name}_orchestrate_quiz",
            session_service=session_service,
            auto_create_session=True,
        ),
    }

    return RuntimeBundle(runners_by_type=runners_by_type)


def reset_runtime() -> None:
    build_runtimes.cache_clear()


def extract_final_text(events: Iterable) -> str:
    for event in events:
        if event.is_final_response() and event.content:
            return "".join(part.text or "" for part in event.content.parts).strip()
    raise RuntimeError("The orchestrator run completed without a final text response.")


def extract_agent_type(prompt: str) -> str:
    match = re.search(r"(?im)^\s*agent_type(?:_intent)?\s*:\s*([a-z_]+)\s*$", prompt)
    if not match:
        supported = ", ".join(SUPPORTED_AGENT_TYPES)
        raise ValueError(
            "Deterministic routing requires an explicit agent type. "
            f"Add a line like 'agent_type: explain'. Supported values: {supported}."
        )

    agent_type = match.group(1).strip().lower()
    if agent_type not in SUPPORTED_AGENT_TYPES:
        supported = ", ".join(SUPPORTED_AGENT_TYPES)
        raise ValueError(f"Unsupported agent_type '{agent_type}'. Supported values: {supported}.")
    return agent_type


def extract_user_request(prompt: str) -> str:
    lines = []
    for line in prompt.splitlines():
        if re.match(r"(?im)^\s*agent_type(?:_intent)?\s*:\s*[a-z_]+\s*$", line):
            continue
        if re.match(r"(?im)^\s*request\s*:\s*", line):
            lines.append(re.sub(r"(?im)^\s*request\s*:\s*", "", line).strip())
            continue
        lines.append(line.strip())

    cleaned = "\n".join(line for line in lines if line).strip()
    if not cleaned:
        raise ValueError("Include the user request after the agent_type line.")
    return cleaned


def _build_routed_prompt(agent_type: str, user_request: str) -> str:
    return (
        f"Agent type intent: {agent_type}\n"
        f"User request: {user_request}\n\n"
        "Stay within your assigned agent role."
    )


def _run_agent(runner: Runner, prompt: str, user_id: str, session_id: str) -> str:
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    events = runner.run(user_id=user_id, session_id=session_id, new_message=message)
    return extract_final_text(events)


def run_prompt(prompt: str, user_id: str = "demo-user", session_id: str | None = None) -> str:
    runtime = build_runtimes()
    agent_type = extract_agent_type(prompt)
    user_request = extract_user_request(prompt)
    resolved_session_id = session_id or str(uuid.uuid4())

    runner = runtime.runners_by_type[agent_type]
    final_text = _run_agent(
        runner,
        _build_routed_prompt(agent_type, user_request),
        user_id=user_id,
        session_id=f"{resolved_session_id}-{agent_type}",
    )

    return "\n".join(
        [
            f"### Orchestrator route: {agent_type}",
            final_text,
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Module 03 deterministic orchestrator example.")
    parser.add_argument(
        "prompt",
        nargs="?",
        default="agent_type: explain\nrequest: Explain what an agent orchestrator does.",
        help="Prompt containing agent_type and request lines.",
    )
    args = parser.parse_args()

    print(run_prompt(args.prompt))


if __name__ == "__main__":
    main()
