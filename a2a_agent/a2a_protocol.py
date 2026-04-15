"""Small A2A protocol helpers for Module 12.

This file intentionally stays framework-light so the same logic can run in:
- the local banking assistant agent runner (`main.py`)
- tests
- future integrations that do not depend on ADK internals
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class A2AError(RuntimeError):
    """Raised when a remote A2A peer cannot complete a protocol step."""


@dataclass(frozen=True)
class TaskHandle:
    task_id: str
    status: str


def _normalize_base_url(base_url: str) -> str:
    cleaned = base_url.strip().rstrip("/")
    if not cleaned:
        raise A2AError("A2A base URL must not be empty.")
    return cleaned


def _join(base_url: str, path: str) -> str:
    normalized = _normalize_base_url(base_url)
    return f"{normalized}{path}"


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: float = 8.0) -> dict[str, Any]:
    data: bytes | None = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise A2AError(f"A2A request failed ({method} {url}): {exc}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise A2AError(f"A2A response was not valid JSON ({method} {url}).") from exc
    if not isinstance(parsed, dict):
        raise A2AError(f"A2A response must be a JSON object ({method} {url}).")
    return parsed


def discover_agent_card(agent_base_url: str, timeout: float = 8.0) -> dict[str, Any]:
    url = _join(agent_base_url, "/.well-known/agent-card")
    card = _http_json("GET", url, timeout=timeout)
    if "capabilities" not in card:
        raise A2AError("Agent Card missing required field: capabilities.")
    return card


def create_task(
    agent_base_url: str,
    goal: str,
    context: dict[str, Any],
    timeout: float = 8.0,
) -> TaskHandle:
    url = _join(agent_base_url, "/a2a/tasks")
    payload = {
        "goal": goal,
        "context": context,
    }
    created = _http_json("POST", url, payload=payload, timeout=timeout)
    task_id = str(created.get("task_id", "")).strip()
    if not task_id:
        raise A2AError("Task creation response did not include task_id.")
    return TaskHandle(task_id=task_id, status=str(created.get("status", "queued")))


def get_task(agent_base_url: str, task_id: str, timeout: float = 8.0) -> dict[str, Any]:
    quoted_task_id = urllib.parse.quote(task_id, safe="")
    url = _join(agent_base_url, f"/a2a/tasks/{quoted_task_id}")
    return _http_json("GET", url, timeout=timeout)


def wait_for_final_artifact(
    agent_base_url: str,
    task_id: str,
    timeout_seconds: float = 20.0,
    poll_interval_seconds: float = 0.35,
    request_timeout: float = 8.0,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    started_at = time.monotonic()
    timeline: list[dict[str, Any]] = []

    while True:
        snapshot = get_task(agent_base_url, task_id=task_id, timeout=request_timeout)
        status = str(snapshot.get("status", "unknown"))
        timeline.append(
            {
                "status": status,
                "progress_message": snapshot.get("progress_message", ""),
            }
        )
        if status == "completed":
            artifact = snapshot.get("artifact")
            if not isinstance(artifact, dict):
                raise A2AError("Completed task did not include an artifact object.")
            return artifact, timeline
        if status in {"failed", "cancelled"}:
            raise A2AError(f"Remote specialist returned terminal status '{status}'.")
        if time.monotonic() - started_at > timeout_seconds:
            raise A2AError(f"A2A task timed out after {timeout_seconds:.1f}s.")
        time.sleep(max(poll_interval_seconds, 0.05))

