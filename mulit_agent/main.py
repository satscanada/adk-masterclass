from __future__ import annotations

import argparse
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from simple_litellm_agent.config import get_settings

from .agent import create_bullet_agent, create_writer_agent


@dataclass(frozen=True)
class RuntimeBundle:
    writer_runner: Runner
    bullet_runner: Runner


@lru_cache(maxsize=1)
def build_runtimes() -> RuntimeBundle:
    settings = get_settings()
    session_service = InMemorySessionService()

    writer_runner = Runner(
        agent=create_writer_agent(settings),
        app_name=f"{settings.app_name}_multi_writer",
        session_service=session_service,
        auto_create_session=True,
    )
    bullet_runner = Runner(
        agent=create_bullet_agent(settings),
        app_name=f"{settings.app_name}_multi_bullets",
        session_service=session_service,
        auto_create_session=True,
    )

    return RuntimeBundle(writer_runner=writer_runner, bullet_runner=bullet_runner)


def reset_runtime() -> None:
    build_runtimes.cache_clear()


def extract_final_text(events: Iterable) -> str:
    for event in events:
        if event.is_final_response() and event.content:
            return "".join(part.text or "" for part in event.content.parts).strip()
    raise RuntimeError("The multi-agent run completed without a final text response.")


def _run_agent(runner: Runner, prompt: str, user_id: str, session_id: str) -> str:
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    events = runner.run(user_id=user_id, session_id=session_id, new_message=message)
    return extract_final_text(events)


def _build_writer_prompt(topic: str) -> str:
    return (
        f"Topic from chat: {topic}\n\n"
        "Write exactly 2 short paragraphs about this topic. "
        "Keep the language simple and easy to learn from."
    )


def _build_bullet_prompt(topic: str) -> str:
    return (
        f"Topic from chat: {topic}\n\n"
        "Return exactly 3 concise bullet points about this topic. "
        "Each bullet must start with '- '."
    )


def run_prompt(prompt: str, user_id: str = "demo-user", session_id: str | None = None) -> str:
    runtime = build_runtimes()
    base_session_id = session_id or str(uuid.uuid4())

    writer_text = _run_agent(
        runtime.writer_runner,
        _build_writer_prompt(prompt),
        user_id=user_id,
        session_id=f"{base_session_id}-writer",
    )
    bullet_text = _run_agent(
        runtime.bullet_runner,
        _build_bullet_prompt(prompt),
        user_id=user_id,
        session_id=f"{base_session_id}-bullets",
    )

    return "\n\n".join(
        [
            "### Agent 1: Paragraph Writer",
            writer_text,
            "### Agent 2: Bullet Summary",
            bullet_text,
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the simple multi-agent ADK example.")
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Artificial intelligence in education",
        help="Topic to send to both agents.",
    )
    args = parser.parse_args()

    print(run_prompt(args.prompt))


if __name__ == "__main__":
    main()

