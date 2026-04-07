from __future__ import annotations

import argparse
import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from functools import lru_cache

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from simple_litellm_agent.config import get_settings

from .agent import create_agent
from .weather_tools import celsius_to_fahrenheit_display

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeBundle:
    runner: Runner


@lru_cache(maxsize=1)
def build_runner() -> RuntimeBundle:
    settings = get_settings()
    session_service = InMemorySessionService()
    app_name = f"{settings.app_name}_module05_advanced"
    runner = Runner(
        agent=create_agent(settings),
        app_name=app_name,
        session_service=session_service,
        auto_create_session=True,
    )
    return RuntimeBundle(runner=runner)


def reset_runtime() -> None:
    build_runner.cache_clear()


def _fallback_text_from_tool_events(events) -> str:
    """Some Gemini/LiteLLM tool runs end with is_final_response and empty content.parts.

    When that happens, we still have structured tool outputs on earlier events — use them.
    """
    weather: dict | None = None
    conversion: dict | None = None
    for event in events:
        for fr in event.get_function_responses():
            name = getattr(fr, "name", None)
            resp = fr.response
            if not isinstance(resp, dict):
                continue
            if name == "fetch_current_weather":
                weather = resp
            elif name == "celsius_to_fahrenheit_display":
                conversion = resp

    if weather and weather.get("status") == "error":
        return str(weather.get("message", "Weather lookup failed."))

    if weather and weather.get("status") == "success":
        c = float(weather["temperature_celsius"])
        if conversion and conversion.get("status") == "success" and conversion.get("formatted"):
            temp_line = str(conversion["formatted"])
        else:
            temp_line = str(celsius_to_fahrenheit_display(c).get("formatted", f"{c} °C"))
        place = weather.get("place_id", "location")
        summary = weather.get("summary", "")
        wind = weather.get("wind_speed")
        wdir = weather.get("wind_dir", "")
        precip = weather.get("precipitation_type", "")
        bits = [
            f"Current weather for **{place}**: {summary}.",
            f"Temperature: {temp_line}.",
        ]
        if wind is not None:
            bits.append(f"Wind: {wind} km/h {wdir}.".strip())
        if precip:
            bits.append(f"Precipitation: {precip}.")
        return "\n".join(bits)

    return ""


def _extract_final_text_core(events) -> tuple[str, str]:
    """Return (text, source) where source is model_final, tool_fallback, or empty string if none."""
    for event in events:
        if not event.is_final_response() or not event.content or not event.content.parts:
            continue
        text = "".join(
            part.text or ""
            for part in event.content.parts
            if not getattr(part, "thought", False)
        ).strip()
        if text:
            return text, "model_final"

    fallback = _fallback_text_from_tool_events(events)
    if fallback:
        return fallback, "tool_fallback"

    return "", ""


def extract_final_text(events) -> str:
    text, source = _extract_final_text_core(events)
    if not text:
        raise RuntimeError("The advanced agent run completed without a final text response.")
    logger.info(
        "advanced_agent reply source=%s via=extract_final_text text_len=%d",
        source,
        len(text),
    )
    return text


def _user_message(prompt: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=prompt)])


def run_prompt(prompt: str, user_id: str = "demo-user", session_id: str | None = None) -> str:
    runtime = build_runner()
    resolved_session_id = session_id or str(uuid.uuid4())
    message = _user_message(prompt)
    # `Runner.run` yields a generator; `extract_final_text` iterates twice (final text + fallback).
    events = list(
        runtime.runner.run(
            user_id=user_id,
            session_id=resolved_session_id,
            new_message=message,
        )
    )
    return extract_final_text(events)


async def stream_prompt(
    prompt: str,
    user_id: str = "demo-user",
    session_id: str | None = None,
) -> AsyncIterator[str]:
    """Yield text chunks from `Runner.run_async()` (tools + NDJSON in the React UI).

    Tool-heavy runs often emit no incremental `part.text` chunks; the final answer is
    still present on the event stream. If no chunks were yielded, we fall back to the same
    `extract_final_text(...)` logic used by blocking `run_prompt`.
    """
    runtime = build_runner()
    resolved_session_id = session_id or str(uuid.uuid4())
    message = _user_message(prompt)

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
        logger.info(
            "advanced_agent reply source=incremental_stream_chunks via=stream_prompt",
        )
        return

    text, source = _extract_final_text_core(accumulated)
    if not text:
        logger.warning(
            "stream_prompt: no streamed chunks and no final text (events=%d)",
            len(accumulated),
        )
        return
    logger.info(
        "advanced_agent reply source=%s via=stream_prompt (no incremental chunks; events=%d) text_len=%d",
        source,
        len(accumulated),
        len(text),
    )
    yield text


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Module 05 weather assistant (tools + LiteLLM).",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="What is the weather in calgary?",
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
