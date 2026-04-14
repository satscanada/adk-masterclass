"""Module 26 runner for sequential retail deposit API workflow."""

from __future__ import annotations

import argparse
import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from simple_litellm_agent.config import get_settings

from .agent import create_agent


@dataclass(frozen=True)
class RuntimeBundle:
    runner: Runner


@lru_cache(maxsize=1)
def build_runner() -> RuntimeBundle:
    settings = get_settings()
    session_service = InMemorySessionService()
    app_name = f"{settings.app_name}_module26_retail_deposit"
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
        if not event.content or not event.content.parts:
            continue
        text = "".join(part.text or "" for part in event.content.parts).strip()
        if text:
            last_text = text
    if not last_text:
        raise RuntimeError("Module 26 completed without producing text output.")
    return last_text


def _strip_markdown_fence(text: str) -> str:
    cleaned = text.strip()
    if not cleaned.startswith("```"):
        return cleaned
    lines = cleaned.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return cleaned


def _extract_json_object(text: str) -> dict:
    candidate = _strip_markdown_fence(text)
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for idx, ch in enumerate(candidate):
        if ch != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(candidate[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise RuntimeError("Module 26 expected a JSON object from the decision agent.")


def run_prompt(prompt: str, user_id: str = "demo-user", session_id: str | None = None) -> str:
    runtime = build_runner()
    resolved_session_id = session_id or str(uuid.uuid4())
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    events = runtime.runner.run(
        user_id=user_id,
        session_id=resolved_session_id,
        new_message=message,
    )
    final_text = extract_final_text(events)
    payload = _extract_json_object(final_text)
    return json.dumps(payload, indent=2, sort_keys=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Module 26 sequential retail deposit workflow and print JSON output.",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="RET-3101",
        help="Customer ID to evaluate (default: RET-3101).",
    )
    args = parser.parse_args()
    print(run_prompt(args.prompt))


if __name__ == "__main__":
    main()
