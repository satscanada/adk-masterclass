"""Optional integration smoke test for advanced_agent streaming.

Loads `.env` from the repo root (WEATHER_API_KEY, LITELLM_*), then:
1) runs async stream_prompt(...) and asserts non-empty combined text
2) optionally hits POST /api/chat/stream via FastAPI TestClient and counts NDJSON delta lines

Skip with exit 0 when required env vars are missing so CI without secrets does not fail.

Run:
  cd /path/to/adk-masterclass
  ./.venv/bin/python tests/advanced_agent_stream_smoke_test.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(PROJECT_ROOT / ".env", override=True)


def _skip(msg: str) -> int:
    print(f"SKIP: {msg}")
    return 0


async def _stream_direct() -> str:
    from advanced_agent.main import reset_runtime, stream_prompt

    reset_runtime()
    parts: list[str] = []
    async for chunk in stream_prompt(
        "What is the weather in calgary?",
        user_id="advanced-stream-smoke",
    ):
        parts.append(chunk)
    return "".join(parts).strip()


def _test_api_stream() -> None:
    from fastapi.testclient import TestClient

    from api_app import app
    from advanced_agent.main import reset_runtime

    reset_runtime()

    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/chat/stream",
            json={
                "agent_key": "advanced_agent",
                "prompt": "What is the weather in calgary?",
                "user_id": "advanced-stream-smoke",
                "session_id": "smoke-session-api",
            },
        ) as response:
            assert response.status_code == 200, response.text
            delta_lines = 0
            buffer = ""
            for chunk in response.iter_bytes():
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    if obj.get("type") == "delta" and obj.get("text"):
                        delta_lines += 1
                    if obj.get("type") == "error":
                        raise AssertionError(obj.get("detail", obj))

            assert delta_lines >= 1, (
                "Expected at least one NDJSON delta line with text from /api/chat/stream; "
                "got 0 deltas. Check LiteLLM, WEATHER_API_KEY, and model tool support."
            )
    print(f"API stream smoke OK ({delta_lines} delta line(s) with text).")


def main() -> int:
    _load_env()

    if not (os.getenv("WEATHER_API_KEY") or "").strip():
        return _skip("WEATHER_API_KEY not set in .env")
    if not (os.getenv("LITELLM_API_BASE") or "").strip():
        return _skip("LITELLM_API_BASE not set in .env")

    text = asyncio.run(_stream_direct())
    if not text:
        print("FAIL: stream_prompt returned empty text.")
        return 1
    print("Direct stream_prompt OK, length:", len(text))
    print(text[:800] + ("..." if len(text) > 800 else ""))

    try:
        _test_api_stream()
    except Exception as exc:  # noqa: BLE001
        print("FAIL: API stream test:", exc)
        return 1

    print("advanced_agent stream smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
