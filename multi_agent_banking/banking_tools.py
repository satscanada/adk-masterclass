"""Mock banking data and tool functions for the Module 07 multi-agent system.

Three tool groups:
  1. Deposit / balance tools  — used by the deposit_agent
  2. Bill / payment tools     — used by the bill_agent
  3. (No extra tools for the decision agent — it reads session.state written by 1 & 2)
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

_TODAY = _dt.date(2026, 4, 6)

# Canonical outcomes for the two demo customers (teaching UI: healthy → approve, weak → deny).
_DEMO_EXPECTED_DECISION: dict[str, str] = {
    "CUST-1001": "APPROVE",
    "CUST-2002": "DENY",
}


_CUSTOMER_DB: dict[str, dict[str, Any]] = {
    "CUST-1001": {
        "name": "Acme Corp",
        "account_number": "BIZ-90210",
        "account_type": "Business Checking",
        "current_balance": 12_480.55,
        "overdraft_limit_requested": 25_000.00,
        "deposits": [
            {"date": "2026-03-02", "amount": 8_500.00, "description": "Client payment — Invoice #1042"},
            {"date": "2026-03-05", "amount": 3_200.00, "description": "POS revenue — Week 9"},
            {"date": "2026-03-10", "amount": 12_000.00, "description": "Client payment — Invoice #1038"},
            {"date": "2026-03-14", "amount": 1_750.00, "description": "POS revenue — Week 10"},
            {"date": "2026-03-18", "amount": 6_400.00, "description": "Client payment — Invoice #1045"},
            {"date": "2026-03-22", "amount": 2_100.00, "description": "POS revenue — Week 11"},
            {"date": "2026-03-25", "amount": 9_300.00, "description": "Client payment — Invoice #1050"},
            {"date": "2026-03-29", "amount": 1_950.00, "description": "POS revenue — Week 12"},
            {"date": "2026-04-01", "amount": 4_800.00, "description": "Client payment — Invoice #1053"},
            {"date": "2026-04-04", "amount": 2_300.00, "description": "POS revenue — Week 13"},
        ],
        "daily_balances": [
            {"date": "2026-03-01", "balance": 4_230.55},
            {"date": "2026-03-05", "balance": 15_930.55},
            {"date": "2026-03-10", "balance": 22_180.55},
            {"date": "2026-03-15", "balance": 14_730.55},
            {"date": "2026-03-20", "balance": 18_630.55},
            {"date": "2026-03-25", "balance": 24_480.55},
            {"date": "2026-03-31", "balance": 5_380.55},
            {"date": "2026-04-04", "balance": 12_480.55},
        ],
        "completed_bills": [
            {"date": "2026-03-03", "amount": 2_500.00, "payee": "Office Lease LLC", "status": "paid"},
            {"date": "2026-03-07", "amount": 850.00, "payee": "AWS Cloud Services", "status": "paid"},
            {"date": "2026-03-12", "amount": 5_750.00, "payee": "Supplier — Raw Materials Co", "status": "paid"},
            {"date": "2026-03-15", "amount": 9_200.00, "payee": "Payroll — March 1st half", "status": "paid"},
            {"date": "2026-03-20", "amount": 1_200.00, "payee": "Insurance Premium", "status": "paid"},
            {"date": "2026-03-25", "amount": 3_450.00, "payee": "Supplier — Packaging Ltd", "status": "paid"},
            {"date": "2026-03-28", "amount": 650.00, "payee": "Utility — Electric & Water", "status": "paid"},
            {"date": "2026-03-31", "amount": 9_200.00, "payee": "Payroll — March 2nd half", "status": "paid"},
            {"date": "2026-04-03", "amount": 1_100.00, "payee": "Marketing — Ad Platform", "status": "paid"},
        ],
        "upcoming_bills": [
            {"due_date": "2026-04-07", "amount": 2_500.00, "payee": "Office Lease LLC", "status": "scheduled"},
            {"due_date": "2026-04-10", "amount": 850.00, "payee": "AWS Cloud Services", "status": "scheduled"},
            {"due_date": "2026-04-12", "amount": 6_100.00, "payee": "Supplier — Raw Materials Co", "status": "scheduled"},
            {"due_date": "2026-04-15", "amount": 9_200.00, "payee": "Payroll — April 1st half", "status": "scheduled"},
            {"due_date": "2026-04-20", "amount": 1_200.00, "payee": "Insurance Premium", "status": "scheduled"},
            {"due_date": "2026-04-25", "amount": 3_700.00, "payee": "Supplier — Packaging Ltd", "status": "scheduled"},
            {"due_date": "2026-04-28", "amount": 680.00, "payee": "Utility — Electric & Water", "status": "pending"},
            {"due_date": "2026-04-30", "amount": 9_200.00, "payee": "Payroll — April 2nd half", "status": "scheduled"},
            {"due_date": "2026-05-03", "amount": 1_100.00, "payee": "Marketing — Ad Platform", "status": "pending"},
        ],
    },
    "CUST-2002": {
        "name": "Sunrise Bakery",
        "account_number": "BIZ-55443",
        "account_type": "Business Checking",
        "current_balance": 1_230.10,
        "overdraft_limit_requested": 10_000.00,
        "deposits": [
            {"date": "2026-03-04", "amount": 980.00, "description": "Daily sales"},
            {"date": "2026-03-11", "amount": 1_100.00, "description": "Daily sales"},
            {"date": "2026-03-18", "amount": 870.00, "description": "Daily sales"},
            {"date": "2026-03-25", "amount": 1_050.00, "description": "Daily sales"},
            {"date": "2026-04-01", "amount": 920.00, "description": "Daily sales"},
        ],
        "daily_balances": [
            {"date": "2026-03-01", "balance": 2_100.10},
            {"date": "2026-03-10", "balance": 1_580.10},
            {"date": "2026-03-15", "balance": 430.10},
            {"date": "2026-03-20", "balance": 800.10},
            {"date": "2026-03-25", "balance": 1_350.10},
            {"date": "2026-03-31", "balance": 310.10},
            {"date": "2026-04-04", "balance": 1_230.10},
        ],
        "completed_bills": [
            {"date": "2026-03-05", "amount": 1_500.00, "payee": "Flour & Ingredients Supplier", "status": "paid"},
            {"date": "2026-03-15", "amount": 2_500.00, "payee": "Staff Wages — March 1st half", "status": "paid"},
            {"date": "2026-03-20", "amount": 500.00, "payee": "Rent — Kitchen Space", "status": "paid"},
            {"date": "2026-03-31", "amount": 2_500.00, "payee": "Staff Wages — March 2nd half", "status": "paid"},
        ],
        "upcoming_bills": [
            {"due_date": "2026-04-05", "amount": 1_500.00, "payee": "Flour & Ingredients Supplier", "status": "scheduled"},
            {"due_date": "2026-04-15", "amount": 2_500.00, "payee": "Staff Wages — April 1st half", "status": "scheduled"},
            {"due_date": "2026-04-20", "amount": 500.00, "payee": "Rent — Kitchen Space", "status": "scheduled"},
            {"due_date": "2026-04-30", "amount": 2_500.00, "payee": "Staff Wages — April 2nd half", "status": "scheduled"},
        ],
    },
}


def _get_customer(customer_id: str) -> dict[str, Any]:
    cid = customer_id.strip().upper()
    if cid not in _CUSTOMER_DB:
        return {"error": f"Customer '{customer_id}' not found. Available demo IDs: {', '.join(sorted(_CUSTOMER_DB))}"}
    return _CUSTOMER_DB[cid]


# ── Deposit / balance tools ──────────────────────────────────────

def get_monthly_deposits(customer_id: str) -> dict[str, Any]:
    """Return deposit transactions for the last calendar month and current month-to-date."""
    data = _get_customer(customer_id)
    if "error" in data:
        return data
    deposits = data["deposits"]
    total = sum(d["amount"] for d in deposits)
    return {
        "customer_id": customer_id.upper(),
        "customer_name": data["name"],
        "account_number": data["account_number"],
        "period": "2026-03-01 to 2026-04-06",
        "deposit_count": len(deposits),
        "total_deposits": total,
        "average_deposit": round(total / max(len(deposits), 1), 2),
        "deposits": deposits,
    }


def get_balance_movement(customer_id: str) -> dict[str, Any]:
    """Return daily balance snapshots to show cash-flow movement across dates."""
    data = _get_customer(customer_id)
    if "error" in data:
        return data
    balances = data["daily_balances"]
    amounts = [b["balance"] for b in balances]
    return {
        "customer_id": customer_id.upper(),
        "customer_name": data["name"],
        "current_balance": data["current_balance"],
        "period": "2026-03-01 to 2026-04-06",
        "min_balance": min(amounts),
        "max_balance": max(amounts),
        "average_balance": round(sum(amounts) / len(amounts), 2),
        "snapshots": balances,
    }


# ── Bill / payment tools ─────────────────────────────────────────

def get_completed_bills(customer_id: str) -> dict[str, Any]:
    """Return bills the customer has already paid in the last month."""
    data = _get_customer(customer_id)
    if "error" in data:
        return data
    bills = data["completed_bills"]
    total = sum(b["amount"] for b in bills)
    return {
        "customer_id": customer_id.upper(),
        "customer_name": data["name"],
        "period": "2026-03-01 to 2026-04-06",
        "bill_count": len(bills),
        "total_paid": total,
        "bills": bills,
    }


def get_upcoming_bills(customer_id: str) -> dict[str, Any]:
    """Return scheduled and pending bills for the next ~30 days."""
    data = _get_customer(customer_id)
    if "error" in data:
        return data
    bills = data["upcoming_bills"]
    total = sum(b["amount"] for b in bills)
    return {
        "customer_id": customer_id.upper(),
        "customer_name": data["name"],
        "period": "2026-04-07 to 2026-05-06",
        "bill_count": len(bills),
        "total_upcoming": total,
        "bills": bills,
    }


# ── Overdraft helper (decision agent reads session.state) ────────

def get_overdraft_request(customer_id: str) -> dict[str, Any]:
    """Return the overdraft limit the customer is requesting."""
    data = _get_customer(customer_id)
    if "error" in data:
        return data
    cid = customer_id.strip().upper()
    return {
        "customer_id": cid,
        "customer_name": data["name"],
        "account_number": data["account_number"],
        "account_type": data["account_type"],
        "current_balance": data["current_balance"],
        "overdraft_limit_requested": data["overdraft_limit_requested"],
        # Lets the decision agent align with fixed mock profiles (UI “healthy” vs “weaker”).
        "demo_expected_decision": _DEMO_EXPECTED_DECISION.get(cid, "CONDITIONAL APPROVE"),
    }
