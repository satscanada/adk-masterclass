from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api_app import app
from advanced_agent.main import reset_runtime as reset_advanced_runtime
from custom_agent.main import reset_runtime as reset_custom_runtime
from multi_agent_banking.main import reset_runtime as reset_banking_runtime
from simple_litellm_agent.main import reset_runtime
from streaming_agent.main import reset_runtime as reset_streaming_runtime

LAST_REQUEST: dict[str, Any] = {}


class MockOpenAIHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        global LAST_REQUEST
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode()
        LAST_REQUEST = {
            "path": self.path,
            "authorization": self.headers.get("Authorization"),
            "content_type": self.headers.get("Content-Type"),
            "json": json.loads(body),
        }

        payload = LAST_REQUEST["json"]
        response = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1712345678,
            "model": payload["model"],
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11},
        }
        encoded = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    server = HTTPServer(("127.0.0.1", 4013), MockOpenAIHandler)  # type: ignore[arg-type]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    os.environ["LITELLM_API_BASE"] = "http://127.0.0.1:4013/v1"
    os.environ["LITELLM_API_KEY"] = "test-key"
    os.environ["LITELLM_MODEL"] = "gemini-3-flash-preview"
    os.environ["LITELLM_PROVIDER"] = "openai"
    os.environ["LITELLM_MAX_TOKENS"] = "32"
    reset_runtime()
    reset_streaming_runtime()
    reset_advanced_runtime()
    reset_custom_runtime()
    reset_banking_runtime()

    try:
        with TestClient(app) as client:
            health = client.get("/health")
            assert health.status_code == 200, health.text
            assert health.json() == {"status": "ok"}, health.text

            agents_response = client.get("/api/agents")
            assert agents_response.status_code == 200, agents_response.text
            agents_payload = agents_response.json()
            expected_agent_count = len(
                json.loads((PROJECT_ROOT / "agents.json").read_text(encoding="utf-8"))["agents"],
            )
            assert len(agents_payload["agents"]) == expected_agent_count, agents_payload
            assert agents_payload["agents"][0]["key"] == "simple_litellm_agent", agents_payload
            streaming_meta = next(a for a in agents_payload["agents"] if a["key"] == "streaming_agent")
            assert streaming_meta["supports_streaming"] is True, streaming_meta
            advanced_meta = next(a for a in agents_payload["agents"] if a["key"] == "advanced_agent")
            assert advanced_meta["supports_streaming"] is True, advanced_meta

            chat_response = client.post(
                "/api/chat",
                json={
                    "agent_key": "simple_litellm_agent",
                    "prompt": "Reply with exactly: ok",
                    "session_id": "api-smoke-test",
                },
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)

    assert chat_response.status_code == 200, chat_response.text
    payload = chat_response.json()
    assert payload["agent_key"] == "simple_litellm_agent", payload
    assert payload["agent_title"] == "Single Agent", payload
    assert payload["session_id"] == "api-smoke-test", payload
    assert payload["response"] == "ok", payload
    assert LAST_REQUEST["path"] == "/v1/chat/completions", LAST_REQUEST
    assert LAST_REQUEST["authorization"] == "Bearer test-key", LAST_REQUEST
    assert LAST_REQUEST["json"]["model"] == "gemini-3-flash-preview", LAST_REQUEST
    assert LAST_REQUEST["json"]["messages"][-1]["content"] == "Reply with exactly: ok", LAST_REQUEST

    print("API smoke test passed.")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
