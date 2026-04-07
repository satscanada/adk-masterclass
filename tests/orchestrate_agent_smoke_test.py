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

from orchestrate_agent.main import reset_runtime, run_prompt
from simple_litellm_agent.config import reset_settings_cache

REQUESTS: list[dict[str, Any]] = []


class MockOpenAIHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode()
        payload = json.loads(body)
        prompt = payload["messages"][-1]["content"]

        REQUESTS.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "json": payload,
            }
        )

        if "Agent type intent: explain" in prompt:
            content = "An orchestrator is the agent that chooses which specialist should handle the request."
        elif "Agent type intent: bullet" in prompt:
            content = "- Picks one specialist\n- Keeps routing deterministic\n- Makes the lesson easy to follow"
        elif "Agent type intent: quiz" in prompt:
            content = "1. What does the orchestrator choose?\n2. Why use agent_type?\n3. Which agent makes bullet points?"
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
    server = HTTPServer(("127.0.0.1", 4014), MockOpenAIHandler)  # type: ignore[arg-type]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    os.environ["LITELLM_API_BASE"] = "http://127.0.0.1:4014/v1"
    os.environ["LITELLM_API_KEY"] = "test-key"
    os.environ["LITELLM_MODEL"] = "gemini-3-flash-preview"
    os.environ["LITELLM_PROVIDER"] = "openai"
    os.environ["LITELLM_MAX_TOKENS"] = "32"

    reset_settings_cache()
    reset_runtime()

    try:
        explain_response = run_prompt(
            "agent_type: explain\nrequest: Explain what an orchestrator does.",
            session_id="orchestrate-explain",
        )
        bullet_response = run_prompt(
            "agent_type: bullet\nrequest: Summarize why deterministic routing helps.",
            session_id="orchestrate-bullet",
        )
        quiz_response = run_prompt(
            "agent_type: quiz\nrequest: Create a quick quiz about orchestrators.",
            session_id="orchestrate-quiz",
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)

    assert "### Orchestrator route: explain" in explain_response, explain_response
    assert "### Orchestrator route: bullet" in bullet_response, bullet_response
    assert "### Orchestrator route: quiz" in quiz_response, quiz_response
    assert len(REQUESTS) == 3, REQUESTS
    assert all(request["path"] == "/v1/chat/completions" for request in REQUESTS), REQUESTS
    assert all(request["authorization"] == "Bearer test-key" for request in REQUESTS), REQUESTS
    assert any("Agent type intent: explain" in request["json"]["messages"][-1]["content"] for request in REQUESTS), REQUESTS
    assert any("Agent type intent: bullet" in request["json"]["messages"][-1]["content"] for request in REQUESTS), REQUESTS
    assert any("Agent type intent: quiz" in request["json"]["messages"][-1]["content"] for request in REQUESTS), REQUESTS
    assert any("User request: Explain what an orchestrator does." in request["json"]["messages"][-1]["content"] for request in REQUESTS), REQUESTS

    try:
        run_prompt("request: Missing the required type")
    except ValueError as exc:
        assert "agent_type" in str(exc), exc
    else:
        raise AssertionError("Expected ValueError when agent_type is missing.")

    print("Orchestrate-agent smoke test passed.")
    print(json.dumps(REQUESTS, indent=2))


if __name__ == "__main__":
    main()
