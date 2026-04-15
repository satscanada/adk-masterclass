"""Module 12 local banking assistant that delegates CD ladder planning over A2A."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from .a2a_protocol import A2AError, create_task, discover_agent_card, wait_for_final_artifact

_CUSTOMER_PROFILES: dict[str, dict[str, Any]] = {
    "SAV-9001": {
        "customer_name": "Maya Patel",
        "available_cash": 50000,
        "emergency_fund_months": 8,
    },
    "SAV-7710": {
        "customer_name": "Jordan Lee",
        "available_cash": 30000,
        "emergency_fund_months": 5,
    },
}

_CUSTOMER_GOALS: dict[str, dict[str, Any]] = {
    "SAV-9001": {
        "time_horizon_years": 5,
        "needs_periodic_liquidity": True,
        "auto_roll_preference": "auto_roll_best_rate",
        "preferred_structure": "1y-2y-3y-4y-5y ladder",
    },
    "SAV-7710": {
        "time_horizon_years": 4,
        "needs_periodic_liquidity": True,
        "auto_roll_preference": "return_cash",
        "preferred_structure": "1y-2y-3y-4y ladder",
    },
}

DEFAULT_A2A_SPECIALIST_URL = "http://127.0.0.1:8720"


def _specialist_url() -> str:
    return os.getenv("MODULE12_A2A_SPECIALIST_URL", DEFAULT_A2A_SPECIALIST_URL).strip() or DEFAULT_A2A_SPECIALIST_URL


def _resolve_customer_id(prompt: str) -> str:
    candidate = prompt.strip().upper()
    if candidate in _CUSTOMER_PROFILES:
        return candidate
    raise ValueError(
        "Module 12 expects a savings customer ID. "
        f"Try one of: {', '.join(sorted(_CUSTOMER_PROFILES))}."
    )


def get_saver_profile(customer_id: str) -> dict[str, Any]:
    try:
        profile = _CUSTOMER_PROFILES[customer_id]
    except KeyError as exc:
        raise ValueError(f"Unknown savings customer_id '{customer_id}'.") from exc
    return {"customer_id": customer_id, **profile}


def get_savings_goal(customer_id: str) -> dict[str, Any]:
    try:
        goals = _CUSTOMER_GOALS[customer_id]
    except KeyError as exc:
        raise ValueError(f"Unknown savings customer_id '{customer_id}'.") from exc
    return {"customer_id": customer_id, **goals}


def _fallback_ladder(profile: dict[str, Any], goals: dict[str, Any]) -> dict[str, Any]:
    available_cash = float(profile["available_cash"])
    terms = [1, 2, 3]
    per_rung = round(available_cash / len(terms), 2)
    return {
        "plan_id": "fallback-rule-based",
        "strategy": "1y-2y-3y mini-ladder (fallback)",
        "rungs": [
            {
                "rung_index": idx + 1,
                "term_years": term,
                "allocation_usd": per_rung,
                "target_apy_percent": round(3.75 + (idx * 0.1), 2),
                "maturity_action": "manual_review",
            }
            for idx, term in enumerate(terms)
        ],
        "blended_target_apy_percent": 3.85,
        "liquidity_note": (
            "Remote specialist unavailable. Generated a conservative mini-ladder "
            "with annual maturity windows."
        ),
        "review_windows": [
            "Schedule banker review 30 days before each maturity.",
            "Re-evaluate rates before entering any rollover instruction.",
        ],
        "source": "local_fallback",
        "goal_snapshot": goals,
    }


def build_cd_ladder(customer_id: str) -> dict[str, Any]:
    profile = get_saver_profile(customer_id)
    goals = get_savings_goal(customer_id)
    remote_url = _specialist_url()

    context = {
        "customer_id": customer_id,
        "available_cash": profile["available_cash"],
        "time_horizon_years": goals["time_horizon_years"],
        "needs_periodic_liquidity": goals["needs_periodic_liquidity"],
        "auto_roll_preference": goals["auto_roll_preference"],
        "preferred_structure": goals["preferred_structure"],
    }

    try:
        card = discover_agent_card(remote_url)
        handle = create_task(
            remote_url,
            goal="Create a CD ladder plan for this customer.",
            context=context,
        )
        artifact, timeline = wait_for_final_artifact(remote_url, handle.task_id)
        return {
            "customer_id": customer_id,
            "customer_name": profile["customer_name"],
            "workflow": "module12_a2a_cd_ladder_v1",
            "delegation_mode": "remote_specialist",
            "agent_card_summary": {
                "agent_name": card.get("agent_name", "unknown"),
                "version": card.get("version", "unknown"),
                "capabilities": card.get("capabilities", {}),
            },
            "task": {
                "task_id": handle.task_id,
                "timeline": timeline,
            },
            "recommendation": artifact,
            "next_action": "Review first maturity 30 days before rollover.",
        }
    except A2AError as exc:
        fallback = _fallback_ladder(profile, goals)
        return {
            "customer_id": customer_id,
            "customer_name": profile["customer_name"],
            "workflow": "module12_a2a_cd_ladder_v1",
            "delegation_mode": "fallback_rule_based",
            "delegation_error": str(exc),
            "recommendation": fallback,
            "next_action": "Escalate to human banker or retry A2A specialist.",
        }


def run_prompt(prompt: str, user_id: str = "demo-user", session_id: str | None = None) -> str:
    del user_id, session_id  # Maintains the shared registry signature.
    customer_id = _resolve_customer_id(prompt)
    payload = build_cd_ladder(customer_id)
    return json.dumps(payload, indent=2, sort_keys=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Module 12 A2A CD ladder delegation flow.",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="SAV-9001",
        help="Savings customer ID (default: SAV-9001).",
    )
    args = parser.parse_args()
    print(run_prompt(args.prompt))


if __name__ == "__main__":
    main()

