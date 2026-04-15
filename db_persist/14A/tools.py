"""Module 14A tools: persistent spending log and deterministic suppression guard."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from google.adk.tools import ToolContext

_MOCK_WEEKLY_SPENDING: dict[str, list[dict[str, object]]] = {
    "CUST-3001": [
        {"week": "2026-W10", "category": "dining", "amount": 280.0},
        {"week": "2026-W11", "category": "dining", "amount": 340.0},
        {"week": "2026-W12", "category": "dining", "amount": 410.0},
    ],
    "CUST-3002": [
        {"week": "2026-W10", "category": "dining", "amount": 220.0},
        {"week": "2026-W11", "category": "dining", "amount": 215.0},
        {"week": "2026-W12", "category": "dining", "amount": 230.0},
    ],
    "CUST-3003": [
        {"week": "2026-W10", "category": "grocery", "amount": 190.0},
        {"week": "2026-W11", "category": "grocery", "amount": 260.0},
        {"week": "2026-W12", "category": "grocery", "amount": 330.0},
    ],
}

_ALLOWED_RESPONSES = {"accepted", "declined", "not_now"}


def _records_for_customer(state: dict, customer_id: str) -> list[dict]:
    rows = state.get("spending_log", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("customer_id") == customer_id]


def get_weekly_transactions(customer_id: str, tool_context: ToolContext) -> dict:
    """Return deterministic weekly spend snapshot for this run."""
    rows = _MOCK_WEEKLY_SPENDING.get(customer_id)
    if not rows:
        raise ValueError(
            f"Unknown customer '{customer_id}'. Expected one of: "
            f"{', '.join(sorted(_MOCK_WEEKLY_SPENDING))}."
        )

    existing_records = _records_for_customer(tool_context.state, customer_id)
    next_index = min(len(existing_records), len(rows) - 1)
    snapshot = rows[next_index]
    return {
        "customer_id": customer_id,
        "snapshot": snapshot,
        "history_weeks_available": len(rows),
        "log_entries_for_customer": len(existing_records),
    }


def append_spending_snapshot(
    customer_id: str,
    week: str,
    category: str,
    amount: float,
    tool_context: ToolContext,
) -> dict:
    """Append one weekly snapshot to session.state['spending_log']."""
    log = tool_context.state.get("spending_log", [])
    if not isinstance(log, list):
        log = []

    log.append(
        {
            "customer_id": customer_id,
            "week": week,
            "category": category,
            "amount": float(amount),
            "recorded_at": datetime.now(UTC).isoformat(),
        }
    )
    tool_context.state["spending_log"] = log
    return {
        "appended": True,
        "customer_id": customer_id,
        "log_length_total": len(log),
        "log_length_customer": len(_records_for_customer(tool_context.state, customer_id)),
    }


def check_trend_and_suppression(customer_id: str, tool_context: ToolContext) -> dict:
    """Detect rising spend and apply 30-day decline suppression deterministically."""
    customer_log = _records_for_customer(tool_context.state, customer_id)
    if len(customer_log) < 3:
        return {
            "trend_detected": False,
            "suppressed": False,
            "reason": "insufficient_data",
            "required_entries": 3,
            "current_entries": len(customer_log),
        }

    recent = customer_log[-3:]
    categories = {str(row.get("category", "")).lower() for row in recent}
    if len(categories) != 1:
        return {
            "trend_detected": False,
            "suppressed": False,
            "reason": "mixed_categories",
        }

    amounts = [float(row.get("amount", 0.0)) for row in recent]
    if amounts[0] <= 0:
        pct_increase = 0.0
    else:
        pct_increase = round(((amounts[2] - amounts[0]) / amounts[0]) * 100, 1)
    trend_detected = amounts[0] < amounts[1] < amounts[2] and pct_increase >= 10.0

    suggestion_history = tool_context.state.get("suggestion_history", [])
    if not isinstance(suggestion_history, list):
        suggestion_history = []
    cutoff = datetime.now(UTC) - timedelta(days=30)
    category = str(recent[-1].get("category", "")).lower()
    suppressed = False
    for item in suggestion_history:
        if not isinstance(item, dict):
            continue
        if str(item.get("customer_id", "")).upper() != customer_id.upper():
            continue
        if str(item.get("category", "")).lower() != category:
            continue
        if str(item.get("response", "")).lower() != "declined":
            continue
        try:
            recorded_at = datetime.fromisoformat(str(item.get("recorded_at", "")))
        except ValueError:
            continue
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=UTC)
        if recorded_at > cutoff:
            suppressed = True
            break

    return {
        "trend_detected": trend_detected,
        "suppressed": suppressed if trend_detected else False,
        "reason": "cooling_window_active" if trend_detected and suppressed else "ok",
        "category": category,
        "amounts": amounts,
        "pct_increase": pct_increase,
    }


def record_suggestion_response(
    customer_id: str,
    category: str,
    response: str,
    tool_context: ToolContext,
) -> dict:
    """Store accepted/declined/not_now suggestion response in session state."""
    normalized = response.strip().lower()
    if normalized not in _ALLOWED_RESPONSES:
        raise ValueError(
            "response must be one of: accepted, declined, not_now",
        )

    history = tool_context.state.get("suggestion_history", [])
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "customer_id": customer_id,
            "category": category.lower(),
            "response": normalized,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
    )
    tool_context.state["suggestion_history"] = history
    return {
        "recorded": True,
        "response": normalized,
        "history_length_total": len(history),
    }
