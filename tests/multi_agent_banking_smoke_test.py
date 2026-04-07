"""Smoke test for the Module 07 multi-agent banking pipeline.

Starts a mock OpenAI-compatible server, points the banking pipeline at it,
and verifies that:
  1. All three pipeline agents (deposit, bill, decision) send LLM requests
  2. The tool functions are called — the LLM messages reference tool output
  3. The combined response contains the pipeline banner
  4. Both demo customers (CUST-1001 and CUST-2002) produce valid output
  5. An invalid customer ID surfaces a clear error from the tools

Run:
  cd /path/to/adk-masterclass
  ./.venv/bin/python tests/multi_agent_banking_smoke_test.py
"""

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

from multi_agent_banking.banking_tools import (
    get_balance_movement,
    get_completed_bills,
    get_monthly_deposits,
    get_overdraft_request,
    get_upcoming_bills,
)

REQUESTS: list[dict[str, Any]] = []


class MockOpenAIHandler(BaseHTTPRequestHandler):
    """Returns canned banking-flavored responses for each pipeline stage."""

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode()
        payload = json.loads(body)
        messages = payload.get("messages", [])
        all_text_parts: list[str] = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                all_text_parts.append(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, str):
                        all_text_parts.append(part)
                    elif isinstance(part, dict) and "text" in part:
                        all_text_parts.append(part["text"])
        combined = " ".join(all_text_parts).lower()

        REQUESTS.append({
            "path": self.path,
            "authorization": self.headers.get("Authorization"),
            "json": payload,
        })

        if "deposit" in combined and "balance" in combined:
            content = (
                "## Deposit & Balance Analysis\n"
                "Total deposits: $52,300 across 10 transactions.\n"
                "Average deposit: $5,230. Balance trend: stable.\n"
                "Cash-flow health: **strong**."
            )
        elif "bill" in combined and ("completed" in combined or "upcoming" in combined):
            content = (
                "## Bill Payment Analysis\n"
                "Total paid last month: $33,900 across 9 bills.\n"
                "Upcoming obligations: $34,530 across 9 bills.\n"
                "Liability outlook: **manageable**."
            )
        elif "credit officer" in combined or "overdraft" in combined:
            content = (
                "## Overdraft Decision\n"
                "**Decision**: APPROVE\n"
                "**Recommended Limit**: $25,000\n"
                "**Risk Rating**: Low\n"
                "**Key Factors**:\n"
                "- Strong deposit inflow\n"
                "- Stable balance history\n"
                "- Manageable upcoming obligations"
            )
        else:
            content = "ok"

        tool_calls = payload.get("tool_calls") or []
        for msg in messages:
            if isinstance(msg.get("tool_calls"), list):
                tool_calls.extend(msg["tool_calls"])

        response = {
            "id": "chatcmpl-banking-test",
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
            "usage": {"prompt_tokens": 50, "completion_tokens": 60, "total_tokens": 110},
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
    server = HTTPServer(("127.0.0.1", 4015), MockOpenAIHandler)  # type: ignore[arg-type]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    os.environ["LITELLM_API_BASE"] = "http://127.0.0.1:4015/v1"
    os.environ["LITELLM_API_KEY"] = "test-key"
    os.environ["LITELLM_MODEL"] = "gemini-3-flash-preview"
    os.environ["LITELLM_PROVIDER"] = "openai"
    os.environ["LITELLM_MAX_TOKENS"] = "64"

    from simple_litellm_agent.config import reset_settings_cache
    from multi_agent_banking.main import reset_runtime, run_prompt

    reset_settings_cache()
    reset_runtime()

    try:
        # ── Test 1: CUST-1001 (healthy customer) ────────────────────
        REQUESTS.clear()
        response_1001 = run_prompt("CUST-1001", session_id="banking-smoke-1001")

        # ── Test 2: CUST-2002 (weaker customer) ─────────────────────
        reset_runtime()
        REQUESTS.clear()
        response_2002 = run_prompt("CUST-2002", session_id="banking-smoke-2002")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)

    # ── Assertions: CUST-1001 ───────────────────────────────────────
    assert "Pipeline:" in response_1001, f"Missing pipeline banner: {response_1001[:200]}"
    assert "deposit_agent" in response_1001, f"Missing deposit_agent in banner: {response_1001[:200]}"
    assert "bill_agent" in response_1001, f"Missing bill_agent in banner: {response_1001[:200]}"
    assert "decision_agent" in response_1001, f"Missing decision_agent in banner: {response_1001[:200]}"
    assert len(response_1001) > 100, f"Response too short ({len(response_1001)} chars)"
    print("CUST-1001 response OK, length:", len(response_1001))

    # ── Assertions: CUST-2002 ───────────────────────────────────────
    assert "Pipeline:" in response_2002, f"Missing pipeline banner: {response_2002[:200]}"
    assert len(response_2002) > 100, f"Response too short ({len(response_2002)} chars)"
    print("CUST-2002 response OK, length:", len(response_2002))

    # ── Assertions: tool functions return valid data ────────────────
    deposits = get_monthly_deposits("CUST-1001")
    assert deposits["deposit_count"] == 10, deposits
    assert deposits["total_deposits"] == 52_300.00, deposits

    balances = get_balance_movement("CUST-1001")
    assert balances["min_balance"] == 4230.55, balances
    assert balances["max_balance"] == 24480.55, balances

    bills_paid = get_completed_bills("CUST-1001")
    assert bills_paid["bill_count"] == 9, bills_paid

    bills_upcoming = get_upcoming_bills("CUST-1001")
    assert bills_upcoming["bill_count"] == 9, bills_upcoming

    overdraft = get_overdraft_request("CUST-1001")
    assert overdraft["overdraft_limit_requested"] == 25_000.00, overdraft
    assert overdraft["customer_name"] == "Acme Corp", overdraft

    # ── Assertions: invalid customer ────────────────────────────────
    bad = get_monthly_deposits("INVALID-ID")
    assert "error" in bad, f"Expected error for invalid customer: {bad}"
    assert "INVALID-ID" in bad["error"], bad

    print("\nMulti-agent banking smoke test passed.")
    print("CUST-1001 response preview:")
    print(response_1001[:500])


if __name__ == "__main__":
    main()
