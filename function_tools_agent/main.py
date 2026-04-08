"""Module 09 CLI runner."""

from __future__ import annotations

import argparse
import json
import time
import uuid
from collections.abc import Iterable

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from simple_litellm_agent.config import get_settings

from .agent import (
    create_celery_banking_agent,
    create_agent_as_tool_root_agent,
    create_basic_tools_agent,
    create_long_running_tools_agent,
)
from .function_tools import reset_long_running_state

SCENARIOS = ("basic", "long-running", "agent-as-tool", "celery")


def _extract_last_text(events: Iterable) -> str:
    last_text = ""
    for event in events:
        if not event.content or not event.content.parts:
            continue
        text = "".join(part.text or "" for part in event.content.parts).strip()
        if text:
            last_text = text
    if not last_text:
        raise RuntimeError("No final text output produced.")
    return last_text


def _runner_for(scenario: str) -> Runner:
    settings = get_settings()
    session_service = InMemorySessionService()
    if scenario == "basic":
        agent = create_basic_tools_agent(settings)
    elif scenario == "long-running":
        agent = create_long_running_tools_agent(settings)
    elif scenario == "agent-as-tool":
        agent = create_agent_as_tool_root_agent(settings)
    elif scenario == "celery":
        agent = create_celery_banking_agent(settings)
    else:
        raise ValueError(f"Unsupported scenario '{scenario}'.")
    return Runner(
        agent=agent,
        app_name=f"{settings.app_name}_module09_{scenario.replace('-', '_')}",
        session_service=session_service,
        auto_create_session=True,
    )


def _user_message(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])


def _run_simple(runner: Runner, prompt: str, user_id: str, session_id: str) -> str:
    try:
        events = list(
            runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=_user_message(prompt),
            )
        )
    except Exception as exc:
        raise RuntimeError(f"Runner execution failed before final output: {exc}") from exc
    return _extract_last_text(events)


def _run_long_running(runner: Runner, prompt: str, user_id: str, session_id: str) -> str:
    try:
        first_pass = list(
            runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=_user_message(prompt),
            )
        )
    except Exception as exc:
        raise RuntimeError(f"Long-running turn 1 failed before final output: {exc}") from exc
    first_text = _extract_last_text(first_pass)

    function_call_id: str | None = None
    ticket_id: str | None = None
    customer_id: str = "RET-4420"

    for event in first_pass:
        if not event.content or not event.content.parts:
            continue
        for part in event.content.parts:
            fc = getattr(part, "function_call", None)
            if fc and getattr(fc, "name", "") == "ask_for_exception_clearance":
                function_call_id = getattr(fc, "id", None)
                args = getattr(fc, "args", None) or {}
                if isinstance(args, dict):
                    customer_id = str(args.get("customer_id", customer_id))
            fr = getattr(part, "function_response", None)
            if fr and getattr(fr, "name", "") == "ask_for_exception_clearance":
                response = getattr(fr, "response", None) or {}
                if isinstance(response, dict):
                    ticket_id = str(response.get("ticket_id", "") or "")

    if not function_call_id:
        return first_text

    approval_response = types.FunctionResponse(
        id=function_call_id,
        name="ask_for_exception_clearance",
        response={
            "status": "approved",
            "ticket_id": ticket_id or f"TKT-{uuid.uuid4().hex[:8].upper()}",
            "customer_id": customer_id.strip().upper(),
        },
    )
    try:
        second_pass = list(
            runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(function_response=approval_response)],
                ),
            )
        )
    except Exception as exc:
        raise RuntimeError(f"Long-running turn 2 failed before final output: {exc}") from exc
    second_text = _extract_last_text(second_pass)
    return (
        "## Turn 1 (pending)\n"
        f"{first_text}\n\n"
        "## Turn 2 (approval response + completion)\n"
        f"{second_text}"
    )


def _extract_celery_tool_events(events: Iterable) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    submit_payload: dict[str, object] | None = None
    status_payload: dict[str, object] | None = None
    for event in events:
        if not event.content or not event.content.parts:
            continue
        for part in event.content.parts:
            fr = getattr(part, "function_response", None)
            if not fr:
                continue
            name = getattr(fr, "name", "") or ""
            response = getattr(fr, "response", None)
            if not isinstance(response, dict):
                continue
            if name == "submit_deposit_recalc_task":
                submit_payload = response
            elif name == "get_deposit_recalc_task_status":
                status_payload = response
    return submit_payload, status_payload


def _is_pending_like_status(status_payload: dict[str, object] | None) -> bool:
    if not status_payload:
        return False
    state = str(status_payload.get("state", "")).upper()
    ready = bool(status_payload.get("ready", False))
    return not ready and state in {"PENDING", "PROGRESS", "STARTED", "RETRY"}


def _run_celery(
    runner: Runner,
    prompt: str,
    user_id: str,
    session_id: str,
    *,
    show_tool_events: bool,
    poll_task: bool,
    poll_interval: float,
    poll_timeout: float,
    status_grace_seconds: float,
) -> str:
    try:
        events = list(
            runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=_user_message(prompt),
            )
        )
    except Exception as exc:
        raise RuntimeError(f"Celery scenario failed before final output: {exc}") from exc

    final_text = _extract_last_text(events)
    submit_payload, status_payload = _extract_celery_tool_events(events)

    prefix_parts: list[str] = []
    task_id = None
    if submit_payload and isinstance(submit_payload, dict):
        task_id = submit_payload.get("task_id")
    if show_tool_events:
        if submit_payload:
            prefix_parts.append("## Tool event: submit_deposit_recalc_task")
            prefix_parts.append(json.dumps(submit_payload, indent=2, default=str))
        if status_payload:
            prefix_parts.append("## Tool event: get_deposit_recalc_task_status")
            prefix_parts.append(json.dumps(status_payload, indent=2, default=str))

    # Demo-friendly behavior: if the first status check is still pending, wait a bit
    # and ask the agent for one more status pass so final reply is less likely pending.
    if (
        not poll_task
        and task_id
        and _is_pending_like_status(status_payload)
        and status_grace_seconds > 0
    ):
        time.sleep(status_grace_seconds)
        follow_up = (
            f"Re-check the async task status for task_id {task_id} now and "
            "share the latest state/result."
        )
        try:
            second_events = list(
                runner.run(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=_user_message(follow_up),
                )
            )
        except Exception as exc:
            raise RuntimeError(f"Celery follow-up status check failed: {exc}") from exc
        final_text = _extract_last_text(second_events)
        _, second_status_payload = _extract_celery_tool_events(second_events)
        if show_tool_events and second_status_payload:
            prefix_parts.append("## Tool event: get_deposit_recalc_task_status (after app wait)")
            prefix_parts.append(json.dumps(second_status_payload, indent=2, default=str))
        prefix_parts.append(
            f"## App wait before re-check\nSlept {status_grace_seconds:.1f}s before second status check."
        )

    if poll_task and task_id:
        from .function_tools import get_deposit_recalc_task_status

        started = time.time()
        poll_lines: list[str] = ["## Auto-poll status"]
        while True:
            status = get_deposit_recalc_task_status(str(task_id))
            poll_lines.append(json.dumps(status, default=str))
            if status.get("ready"):
                break
            if (time.time() - started) >= poll_timeout:
                poll_lines.append(
                    json.dumps(
                        {"status": "timeout", "message": f"Polling timed out after {poll_timeout:.1f}s"},
                        default=str,
                    )
                )
                break
            time.sleep(max(poll_interval, 0.1))
        prefix_parts.append("\n".join(poll_lines))
    elif poll_task and not task_id:
        prefix_parts.append("## Auto-poll status\nNo task_id found in submit response; skipping polling.")

    if prefix_parts:
        return "\n\n".join(prefix_parts) + "\n\n## Model summary\n" + final_text
    return final_text


def run_prompt(
    prompt: str,
    scenario: str = "basic",
    *,
    show_tool_events: bool = False,
    poll_task: bool = False,
    poll_interval: float = 1.5,
    poll_timeout: float = 30.0,
    status_grace_seconds: float = 3.0,
) -> str:
    reset_long_running_state()
    runner = _runner_for(scenario)
    user_id = "demo-user"
    session_id = str(uuid.uuid4())
    if scenario == "long-running":
        return _run_long_running(runner, prompt, user_id, session_id)
    if scenario == "celery":
        return _run_celery(
            runner,
            prompt,
            user_id,
            session_id,
            show_tool_events=show_tool_events,
            poll_task=poll_task,
            poll_interval=poll_interval,
            poll_timeout=poll_timeout,
            status_grace_seconds=status_grace_seconds,
        )
    return _run_simple(runner, prompt, user_id, session_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Module 09 examples: basic function tools, long-running tools, and agent-as-a-tool.",
    )
    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default="basic",
        help="Module 09 scenario to run (default: basic).",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="RET-3101",
        help=(
            "Input prompt (default: RET-3101). "
            "For long-running try: 'Request manual approval for RET-4420 due to source-of-funds check'."
        ),
    )
    parser.add_argument(
        "--show-tool-events",
        action="store_true",
        help="For celery scenario: print raw tool responses (includes task_id).",
    )
    parser.add_argument(
        "--poll-task",
        action="store_true",
        help="For celery scenario: auto-poll task status until ready or timeout.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.5,
        help="For --poll-task: seconds between status polls (default: 1.5).",
    )
    parser.add_argument(
        "--poll-timeout",
        type=float,
        default=30.0,
        help="For --poll-task: max seconds to poll before timeout (default: 30).",
    )
    parser.add_argument(
        "--status-grace-seconds",
        type=float,
        default=3.0,
        help=(
            "For celery scenario without --poll-task: if first status is pending, "
            "wait this many seconds and run one follow-up status check (default: 3)."
        ),
    )
    args = parser.parse_args()
    try:
        output = run_prompt(
            args.prompt,
            scenario=args.scenario,
            show_tool_events=args.show_tool_events,
            poll_task=args.poll_task,
            poll_interval=args.poll_interval,
            poll_timeout=args.poll_timeout,
            status_grace_seconds=args.status_grace_seconds,
        )
    except RuntimeError as exc:
        msg = str(exc)
        # Common local setup issue: LITELLM_API_BASE unreachable (e.g. 127.0.0.1:4000 down).
        if "Connect call failed" in msg or "Connection error" in msg or "No final text output produced" in msg:
            print("\nModule 09 failed before final LLM output.")
            print("-" * 72)
            print("Likely cause: your LiteLLM/OpenAI-compatible endpoint is unreachable.")
            print("Check these:")
            print("  1) LITELLM_API_BASE in .env (for example http://127.0.0.1:4000/v1)")
            print("  2) The endpoint process is running and reachable")
            print("  3) LITELLM_API_KEY / LITELLM_MODEL are set correctly")
            print("\nOriginal error:")
            print(msg)
            return
        raise
    print(f"\nModule 09 scenario: {args.scenario}")
    print("-" * 72)
    print(output)


if __name__ == "__main__":
    main()

