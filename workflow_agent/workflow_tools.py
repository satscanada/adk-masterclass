"""Mock tools for Module 08 workflow-agent retail deposit scenarios."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_CUSTOMER_DB: dict[str, dict[str, Any]] = {
    "RET-3101": {
        "customer_name": "Aarav Nair",
        "segment": "Mass Affluent",
        "channel": "Mobile + Branch",
        "monthly_income": 185_000.00,
        "avg_month_end_balance": 345_500.00,
        "recent_deposits": [
            {"date": "2026-03-05", "amount": 185_000.00, "mode": "salary"},
            {"date": "2026-03-14", "amount": 42_500.00, "mode": "imps"},
            {"date": "2026-03-24", "amount": 15_000.00, "mode": "cash"},
            {"date": "2026-04-01", "amount": 185_000.00, "mode": "salary"},
        ],
        "risk_signals": {
            "aml_alerts_90d": 0,
            "high_velocity_days_30d": 1,
            "cash_deposit_ratio": 0.06,
        },
        "exceptions_queue": [
            {"reference_id": "EX-3101-01", "issue": "PAN mismatch in slip", "amount": 15_000.00},
            {"reference_id": "EX-3101-02", "issue": "Geo-tag missing for branch capture", "amount": 42_500.00},
        ],
        "requested_offer": "PREMIUM_PLUS",
        "demo_expected_offer": "PREMIUM_PLUS",
    },
    "RET-4420": {
        "customer_name": "Maya Singh",
        "segment": "Emerging Retail",
        "channel": "UPI + Cash",
        "monthly_income": 52_000.00,
        "avg_month_end_balance": 24_300.00,
        "recent_deposits": [
            {"date": "2026-03-04", "amount": 9_000.00, "mode": "cash"},
            {"date": "2026-03-11", "amount": 11_500.00, "mode": "upi"},
            {"date": "2026-03-19", "amount": 8_200.00, "mode": "cash"},
            {"date": "2026-03-27", "amount": 13_000.00, "mode": "upi"},
        ],
        "risk_signals": {
            "aml_alerts_90d": 2,
            "high_velocity_days_30d": 6,
            "cash_deposit_ratio": 0.48,
        },
        "exceptions_queue": [
            {"reference_id": "EX-4420-01", "issue": "Source of funds declaration pending", "amount": 9_000.00},
            {"reference_id": "EX-4420-02", "issue": "Address proof refresh needed", "amount": 8_200.00},
            {"reference_id": "EX-4420-03", "issue": "UPI alias ownership mismatch", "amount": 13_000.00},
        ],
        "requested_offer": "PREMIUM_PLUS",
        "demo_expected_offer": "SAFE_GROWTH",
    },
}

_EXCEPTION_CURSOR: dict[str, int] = {}


def reset_workflow_state() -> None:
    """Reset loop cursor so each run starts from the first exception."""
    _EXCEPTION_CURSOR.clear()


def _get_customer(customer_id: str) -> dict[str, Any]:
    cid = customer_id.strip().upper()
    if cid not in _CUSTOMER_DB:
        return {
            "error": (
                f"Customer '{customer_id}' not found. "
                f"Available IDs: {', '.join(sorted(_CUSTOMER_DB))}"
            )
        }
    return _CUSTOMER_DB[cid]


def get_deposit_profile(customer_id: str) -> dict[str, Any]:
    """Return customer profile for retail-deposit underwriting and servicing."""
    data = _get_customer(customer_id)
    if "error" in data:
        return data
    return {
        "customer_id": customer_id.upper(),
        "customer_name": data["customer_name"],
        "segment": data["segment"],
        "channel": data["channel"],
        "monthly_income": data["monthly_income"],
        "avg_month_end_balance": data["avg_month_end_balance"],
    }


def get_recent_deposits(customer_id: str) -> dict[str, Any]:
    """Return recent inbound deposits and derived deposit trend metrics."""
    data = _get_customer(customer_id)
    if "error" in data:
        return data
    deposits = data["recent_deposits"]
    total = sum(item["amount"] for item in deposits)
    cash_total = sum(item["amount"] for item in deposits if item["mode"] == "cash")
    return {
        "customer_id": customer_id.upper(),
        "customer_name": data["customer_name"],
        "deposit_count": len(deposits),
        "total_deposit_amount": total,
        "average_deposit_amount": round(total / max(len(deposits), 1), 2),
        "cash_deposit_share": round(cash_total / max(total, 1), 3),
        "deposits": deposits,
    }


def run_aml_screening(customer_id: str) -> dict[str, Any]:
    """Return AML screening metrics relevant to deposit operations."""
    data = _get_customer(customer_id)
    if "error" in data:
        return data
    rs = data["risk_signals"]
    status = "PASS" if rs["aml_alerts_90d"] == 0 else "REVIEW"
    return {
        "customer_id": customer_id.upper(),
        "customer_name": data["customer_name"],
        "aml_alerts_90d": rs["aml_alerts_90d"],
        "cash_deposit_ratio": rs["cash_deposit_ratio"],
        "aml_status": status,
    }


def run_velocity_check(customer_id: str) -> dict[str, Any]:
    """Return transaction-velocity outcomes used in fraud/risk checks."""
    data = _get_customer(customer_id)
    if "error" in data:
        return data
    rs = data["risk_signals"]
    status = "NORMAL" if rs["high_velocity_days_30d"] <= 2 else "SPIKE_OBSERVED"
    return {
        "customer_id": customer_id.upper(),
        "customer_name": data["customer_name"],
        "high_velocity_days_30d": rs["high_velocity_days_30d"],
        "velocity_status": status,
    }


def fetch_next_deposit_exception(customer_id: str) -> dict[str, Any]:
    """Return the next pending exception item for reconciliation loops."""
    data = _get_customer(customer_id)
    if "error" in data:
        return data
    cid = customer_id.strip().upper()
    cursor = _EXCEPTION_CURSOR.get(cid, 0)
    queue = data["exceptions_queue"]
    if cursor >= len(queue):
        return {
            "customer_id": cid,
            "customer_name": data["customer_name"],
            "has_more": False,
            "message": "No pending deposit exceptions.",
        }
    item = queue[cursor]
    _EXCEPTION_CURSOR[cid] = cursor + 1
    return {
        "customer_id": cid,
        "customer_name": data["customer_name"],
        "has_more": True,
        "pending_item": deepcopy(item),
        "remaining_after_this": len(queue) - (cursor + 1),
    }


def clear_deposit_exception(customer_id: str, reference_id: str) -> dict[str, Any]:
    """Mark an exception item as cleared for audit display purposes."""
    data = _get_customer(customer_id)
    if "error" in data:
        return data
    exists = any(item["reference_id"] == reference_id for item in data["exceptions_queue"])
    if not exists:
        return {
            "customer_id": customer_id.upper(),
            "status": "not_found",
            "reference_id": reference_id,
        }
    return {
        "customer_id": customer_id.upper(),
        "status": "cleared",
        "reference_id": reference_id,
    }


def get_deposit_offer_request(customer_id: str) -> dict[str, Any]:
    """Return requested and expected final offer for deterministic demo outcomes."""
    data = _get_customer(customer_id)
    if "error" in data:
        return data
    return {
        "customer_id": customer_id.upper(),
        "customer_name": data["customer_name"],
        "requested_offer": data["requested_offer"],
        "demo_expected_offer": data["demo_expected_offer"],
    }

