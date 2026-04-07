from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mulit_agent.main import reset_runtime, run_prompt
from simple_litellm_agent.config import reset_settings_cache

REQUESTS: list[dict[str, Any]] = []


class MockOpenAIHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode()
        payload = json.loads(body)

        REQUESTS.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "content_type": self.headers.get("Content-Type"),
                "json": payload,
            }
        )

        user_prompt = payload["messages"][-1]["content"]
        if "Write exactly 2 short paragraphs" in user_prompt:
            content = (
                "Artificial intelligence can help students learn with quick feedback and simple examples. "
                "It can also help teachers create lessons faster.\n\n"
                "When used carefully, it becomes a learning partner that supports practice and understanding. "
                "The goal is to make learning clearer, not more confusing."
            )
        elif "Return exactly 3 concise bullet points" in user_prompt:
            content = "- Fast feedback\n- Better lesson support\n- Clearer practice ideas"
        else:
            content = "unexpected prompt"

        response = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1712345678,
            "model": payload["model"],
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
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

    reset_settings_cache()
    reset_runtime()

    try:
        response = run_prompt("Artificial intelligence in education", session_id="multi-smoke-test")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)

    assert "### Agent 1: Paragraph Writer" in response, response
    assert "### Agent 2: Bullet Summary" in response, response
    assert len(REQUESTS) == 2, REQUESTS
    assert all(request["path"] == "/v1/chat/completions" for request in REQUESTS), REQUESTS
    assert all(request["authorization"] == "Bearer test-key" for request in REQUESTS), REQUESTS
    assert all("Artificial intelligence in education" in request["json"]["messages"][-1]["content"] for request in REQUESTS), REQUESTS
    assert any("Write exactly 2 short paragraphs" in request["json"]["messages"][-1]["content"] for request in REQUESTS), REQUESTS
    assert any("Return exactly 3 concise bullet points" in request["json"]["messages"][-1]["content"] for request in REQUESTS), REQUESTS
    assert "- Fast feedback" in response, response

    print("Multi-agent smoke test passed.")
    print(json.dumps(REQUESTS, indent=2))


if __name__ == "__main__":
    main()

