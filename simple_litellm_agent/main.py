from __future__ import annotations

import argparse
import os
import sys
import uuid
from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter
from typing import Iterable

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import create_agent
from .config import get_settings


@dataclass(frozen=True)
class RuntimeBundle:
    runner: Runner
    session_service: InMemorySessionService
    app_name: str


@lru_cache(maxsize=1)
def build_runner() -> RuntimeBundle:
    settings = get_settings()
    session_service = InMemorySessionService()
    runner = Runner(
        agent=create_agent(settings),
        app_name=settings.app_name,
        session_service=session_service,
        auto_create_session=True,
    )
    return RuntimeBundle(runner=runner, session_service=session_service, app_name=settings.app_name)


def reset_runtime() -> None:
    build_runner.cache_clear()


def extract_final_text(events: Iterable) -> str:
    for event in events:
        if event.is_final_response() and event.content:
            return "".join(part.text or "" for part in event.content.parts).strip()
    raise RuntimeError("The agent run completed without a final text response.")


def _should_show_timing(explicit_value: bool | None) -> bool:
    if explicit_value is not None:
        return explicit_value
    env_value = os.getenv("ADK_SHOW_TIMING", "").strip().lower()
    return env_value in {"1", "true", "yes", "on"}


def run_prompt(
    prompt: str,
    user_id: str = "demo-user",
    session_id: str | None = None,
    show_timing: bool | None = None,
) -> str:
    total_started = perf_counter()
    runner_started = perf_counter()
    runtime = build_runner()
    runner_elapsed = perf_counter() - runner_started

    resolved_session_id = session_id or str(uuid.uuid4())

    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    run_started = perf_counter()
    events = runtime.runner.run(user_id=user_id, session_id=resolved_session_id, new_message=message)
    run_elapsed = perf_counter() - run_started

    extract_started = perf_counter()
    final_text = extract_final_text(events)
    extract_elapsed = perf_counter() - extract_started
    total_elapsed = perf_counter() - total_started

    if _should_show_timing(show_timing):
        print(
            (
                "timing: "
                f"runner_setup={runner_elapsed:.3f}s "
                f"run_call={run_elapsed:.3f}s "
                f"consume_events={extract_elapsed:.3f}s "
                f"total={total_elapsed:.3f}s"
            ),
            file=sys.stderr,
            flush=True,
        )

    return final_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the simple Google ADK + LiteLLM agent.")
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Reply with exactly: ok",
        help="Prompt to send to the agent.",
    )
    parser.add_argument(
        "--timing",
        action="store_true",
        help="Print a small timing breakdown to stderr.",
    )
    args = parser.parse_args()

    print(run_prompt(args.prompt, show_timing=args.timing))


if __name__ == "__main__":
    main()
