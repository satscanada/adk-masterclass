"""Module 11 runner: OpenAPI-backed MCP server consumed by an ADK agent."""

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

from .agent import create_agent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeBundle:
    runner: Runner


@lru_cache(maxsize=1)
def build_runner() -> RuntimeBundle:
    settings = get_settings()
    session_service = InMemorySessionService()
    app_name = f"{settings.app_name}_module11_mcp_server"
    runner = Runner(
        agent=create_agent(settings),
        app_name=app_name,
        session_service=session_service,
        auto_create_session=True,
    )
    return RuntimeBundle(runner=runner)


def reset_runtime() -> None:
    build_runner.cache_clear()


def _extract_last_text(events: Iterable) -> str:
    last_text = ""
    for event in events:
        if not event.content or not event.content.parts:
            continue
        text = "".join(part.text or "" for part in event.content.parts).strip()
        if text:
            last_text = text
    if not last_text:
        raise RuntimeError("The Module 11 MCP run completed without final text output.")
    return last_text


def _user_message(prompt: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=prompt)])


def run_prompt(prompt: str, user_id: str = "demo-user", session_id: str | None = None) -> str:
    runtime = build_runner()
    resolved_session_id = session_id or str(uuid.uuid4())
    message = _user_message(prompt)
    try:
        events = list(
            runtime.runner.run(
                user_id=user_id,
                session_id=resolved_session_id,
                new_message=message,
            )
        )
    except Exception as exc:
        raise RuntimeError(
            "Module 11 MCP run failed. Check MODULE11_MCP_TRANSPORT and Module 11 server config. "
            f"Original error: {exc}"
        ) from exc
    return _extract_last_text(events)


async def stream_prompt(
    prompt: str,
    user_id: str = "demo-user",
    session_id: str | None = None,
) -> AsyncIterator[str]:
    runtime = build_runner()
    resolved_session_id = session_id or str(uuid.uuid4())
    message = _user_message(prompt)

    accumulated: list = []
    yielded_any = False

    try:
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
    except Exception as exc:
        raise RuntimeError(
            "Module 11 MCP stream failed. Check MODULE11_MCP_TRANSPORT and Module 11 server config. "
            f"Original error: {exc}"
        ) from exc

    if yielded_any:
        return

    try:
        final = _extract_last_text(accumulated)
    except RuntimeError as exc:
        logger.warning("stream_prompt: no streamed chunks and no final text: %s", exc)
        return
    if final:
        yield final


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Module 11 MCP server lesson (OpenAPI artifact explorer).",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Search for customer profile operations and generate a mock request and response.",
        help="Prompt to send to the Module 11 MCP-backed agent.",
    )
    args = parser.parse_args()

    async def _run() -> None:
        print("MCP Server Agent: ", end="", flush=True)
        async for piece in stream_prompt(args.prompt):
            print(piece, end="", flush=True)
        print()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
