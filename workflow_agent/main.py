"""Module 08 runner for workflow-agent retail deposit use cases."""

from __future__ import annotations

import argparse
import json
import uuid
from collections.abc import Iterable
from functools import lru_cache
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from simple_litellm_agent.config import get_settings

from .agent import create_composition_agent, create_loop_agent, create_parallel_agent
from .workflow_tools import reset_workflow_state

SCENARIOS = ("loop", "parallel", "composition")

# Workflow orchestrator shells (no LLM) — treat like banking pipeline root for attribution.
_WORKFLOW_SHELLS: frozenset[str] = frozenset({
    "retail_deposit_composition",
    "deposit_parallel_assessment",
    "deposit_exception_loop",
})

_TOOL_TO_AGENT: dict[str, str] = {
    "get_deposit_profile": "deposit_health_agent",
    "get_recent_deposits": "deposit_health_agent",
    "run_aml_screening": "compliance_risk_agent",
    "run_velocity_check": "compliance_risk_agent",
    "fetch_next_deposit_exception": "exception_resolver_agent",
    "clear_deposit_exception": "exception_resolver_agent",
    "get_deposit_offer_request": "final_offer_agent",
}


def normalize_customer_id(raw: str) -> str:
    """Map teaching aliases to demo IDs (matches run_workflow.sh)."""
    key = raw.strip().lower()
    aliases = {
        "strong": "RET-3101",
        "healthy": "RET-3101",
        "ret-3101": "RET-3101",
        "weak": "RET-4420",
        "risk": "RET-4420",
        "ret-4420": "RET-4420",
        "week": "RET-4420",  # common typo for weak
    }
    if key in aliases:
        return aliases[key]
    return raw.strip()


def _safe_dict(obj: Any) -> dict:
    if isinstance(obj, dict):
        return obj
    try:
        return dict(obj)
    except (TypeError, ValueError):
        return {}


def _effective_agent_name(event: Any, current: str | None) -> str | None:
    branch = getattr(event, "branch", None) or ""
    if branch:
        parts = [p for p in branch.split(".") if p.strip()]
        if len(parts) >= 2:
            return parts[-1]
        if len(parts) == 1 and parts[0] not in _WORKFLOW_SHELLS:
            return parts[0]
    author = getattr(event, "author", None)
    if author and author not in ("user", "model"):
        if author in _WORKFLOW_SHELLS:
            return current
        return author
    return current


def _agent_for_tool(tool_name: str) -> str | None:
    return _TOOL_TO_AGENT.get(tool_name)


_TOOL_SUMMARY_FIELDS: dict[str, tuple[str, ...]] = {
    "get_deposit_profile": (
        "customer_id",
        "customer_name",
        "segment",
        "monthly_income",
        "avg_month_end_balance",
    ),
    "get_recent_deposits": (
        "customer_name",
        "deposit_count",
        "total_deposit_amount",
        "average_deposit_amount",
        "cash_deposit_share",
    ),
    "run_aml_screening": ("customer_name", "aml_status", "aml_alerts_90d", "cash_deposit_ratio"),
    "run_velocity_check": ("customer_name", "velocity_status", "high_velocity_days_30d"),
    "clear_deposit_exception": ("customer_id", "status", "reference_id"),
    "get_deposit_offer_request": ("customer_name", "requested_offer", "demo_expected_offer"),
}


def _tool_output_summary(tool_name: str, raw_response: Any) -> dict:
    data = _safe_dict(raw_response)
    if tool_name == "fetch_next_deposit_exception":
        out: dict[str, Any] = {"has_more": data.get("has_more")}
        if "message" in data:
            out["message"] = data["message"]
        pending = data.get("pending_item")
        if isinstance(pending, dict):
            out["reference_id"] = pending.get("reference_id")
            out["issue"] = pending.get("issue")
            out["amount"] = pending.get("amount")
        if "remaining_after_this" in data:
            out["remaining_after_this"] = data["remaining_after_this"]
        return {k: v for k, v in out.items() if v is not None}
    keys = _TOOL_SUMMARY_FIELDS.get(tool_name, ())
    return {k: data[k] for k in keys if k in data}


def _print_audit_trail(events: Iterable[Any]) -> None:
    """Print agent transitions, tool calls, and tool results (terminal-friendly)."""
    current_agent: str | None = None
    for event in events:
        if not event.content or not event.content.parts:
            continue

        effective = _effective_agent_name(event, current_agent)
        if effective and effective != current_agent:
            if current_agent:
                print(f"  [{current_agent}] done", flush=True)
            current_agent = effective
            print(f"  [{current_agent}] started", flush=True)

        acting = effective or current_agent

        for part in event.content.parts:
            fc = getattr(part, "function_call", None)
            if fc:
                tool_name = getattr(fc, "name", "unknown") or "unknown"
                tool_agent = acting or _agent_for_tool(tool_name)
                args = _safe_dict(getattr(fc, "args", None))
                label = tool_agent or "?"
                print(f"    -> {label}.{tool_name}({json.dumps(args, default=str)})", flush=True)
                continue

            fr = getattr(part, "function_response", None)
            if fr:
                tool_name = getattr(fr, "name", "unknown") or "unknown"
                tool_agent = acting or _agent_for_tool(tool_name)
                raw = getattr(fr, "response", None)
                summary = _tool_output_summary(tool_name, raw)
                label = tool_agent or "?"
                print(f"    <- {label}.{tool_name}: {json.dumps(summary, default=str)}", flush=True)
                continue

    if current_agent:
        print(f"  [{current_agent}] done", flush=True)


@lru_cache(maxsize=1)
def _build_session_service() -> InMemorySessionService:
    return InMemorySessionService()


@lru_cache(maxsize=3)
def _build_runner(scenario: str) -> Runner:
    settings = get_settings()
    session_service = _build_session_service()
    app_name = f"{settings.app_name}_module08_workflow_{scenario}"

    if scenario == "loop":
        agent = create_loop_agent(settings)
    elif scenario == "parallel":
        agent = create_parallel_agent(settings)
    elif scenario == "composition":
        agent = create_composition_agent(settings)
    else:
        raise ValueError(f"Unsupported scenario '{scenario}'. Must be one of: {', '.join(SCENARIOS)}")

    return Runner(
        agent=agent,
        app_name=app_name,
        session_service=session_service,
        auto_create_session=True,
    )


def reset_runtime() -> None:
    _build_runner.cache_clear()
    _build_session_service.cache_clear()


def _user_message(prompt: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=prompt)])


def extract_final_text(events: Iterable) -> str:
    last_text = ""
    for event in events:
        if not event.content or not event.content.parts:
            continue
        text = "".join(part.text or "" for part in event.content.parts).strip()
        if text:
            last_text = text
    if not last_text:
        raise RuntimeError("The workflow scenario completed without any text output.")
    return last_text


def run_prompt(
    prompt: str,
    scenario: str = "composition",
    user_id: str = "demo-user",
    session_id: str | None = None,
    *,
    verbose: bool = True,
) -> str:
    resolved_scenario = scenario.strip().lower()
    runner = _build_runner(resolved_scenario)
    resolved_session_id = session_id or str(uuid.uuid4())
    events = list(
        runner.run(
            user_id=user_id,
            session_id=resolved_session_id,
            new_message=_user_message(prompt),
        )
    )
    if verbose:
        print("Audit trail (agent transitions, tool calls, tool results)", flush=True)
        print("-" * 72, flush=True)
        _print_audit_trail(events)
        print("-" * 72, flush=True)
        print("Final assistant response", flush=True)
        print("-" * 72, flush=True)
    return extract_final_text(events)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run Module 08 workflow-agent scenarios for retail deposit operations. "
            "Scenarios: loop, parallel, composition."
        ),
    )
    parser.add_argument(
        "customer_id",
        nargs="?",
        default="RET-3101",
        help="Retail customer ID (default: RET-3101). Try RET-4420 for a higher-risk profile.",
    )
    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default="composition",
        help="Workflow scenario to run (default: composition).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Skip audit trail; print only the final assistant text.",
    )
    args = parser.parse_args()

    reset_workflow_state()
    customer_id = normalize_customer_id(args.customer_id)
    print(f"\nWorkflow Scenario: {args.scenario}", flush=True)
    print(f"Customer: {customer_id}", flush=True)
    if args.customer_id.strip() != customer_id:
        print(f"(normalized from input: {args.customer_id!r})", flush=True)
    print("-" * 72, flush=True)
    output = run_prompt(customer_id, scenario=args.scenario, verbose=not args.quiet)
    if args.quiet:
        print("-" * 72, flush=True)
    print(output, flush=True)


if __name__ == "__main__":
    main()

