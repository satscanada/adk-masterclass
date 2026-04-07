from __future__ import annotations

import argparse
import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from functools import lru_cache

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from simple_litellm_agent.config import get_settings

from .agent import create_agent, routing_banner_markdown

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeBundle:
    runner: Runner


@lru_cache(maxsize=1)
def build_runner() -> RuntimeBundle:
    settings = get_settings()
    session_service = InMemorySessionService()
    app_name = f"{settings.app_name}_module06_custom"
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
    for event in events:
        if event.is_final_response() and event.content:
            return "".join(part.text or "" for part in event.content.parts).strip()
    raise RuntimeError("The custom agent run completed without a final text response.")


def _user_message(prompt: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=prompt)])


def run_prompt(prompt: str, user_id: str = "demo-user", session_id: str | None = None) -> str:
    runtime = build_runner()
    resolved_session_id = session_id or str(uuid.uuid4())
    message = _user_message(prompt)
    events = runtime.runner.run(
        user_id=user_id,
        session_id=resolved_session_id,
        new_message=message,
    )
    return routing_banner_markdown(prompt) + extract_final_text(events)


async def stream_prompt(
    prompt: str,
    user_id: str = "demo-user",
    session_id: str | None = None,
) -> AsyncIterator[str]:
    """Yield assistant text chunks from `Runner.run_async()` (NDJSON in the React UI)."""
    runtime = build_runner()
    resolved_session_id = session_id or str(uuid.uuid4())
    message = _user_message(prompt)

    yield routing_banner_markdown(prompt)

    accumulated: list = []
    yielded_any = False

    async for event in runtime.runner.run_async(
        user_id=user_id,
        session_id=resolved_session_id,
        new_message=message,
    ):
        accumulated.append(event)
        if getattr(event, "author", None) == "user":
            continue
        if not event.content or not event.content.parts:
            continue
        for part in event.content.parts:
            chunk = getattr(part, "text", None) or ""
            if chunk:
                yielded_any = True
                yield chunk

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
        description="Run the Module 06 custom BaseAgent (keyword router + LlmAgent children).",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Explain what a Python list comprehension is in two sentences.",
        help="Prompt to send to the agent.",
    )
    args = parser.parse_args()

    async def _run() -> None:
        print("Agent: ", end="", flush=True)
        async for piece in stream_prompt(args.prompt):
            print(piece, end="", flush=True)
        print()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
