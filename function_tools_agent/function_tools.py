"""Module 09 tool functions reusing existing banking datasets.

Includes an optional Celery + Redis-backed async tool path.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from multi_agent_banking.banking_tools import get_monthly_deposits, get_overdraft_request
from workflow_agent.workflow_tools import get_deposit_profile, get_recent_deposits

_PENDING_APPROVALS: dict[str, dict[str, Any]] = {}
_CELERY_APP = None
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_env() -> None:
    """Load .env when present (helps direct Celery worker startup)."""
    load_dotenv(ENV_FILE, override=False)


def _redis_url_from_env() -> str:
    """Build Redis URL from env, supporting full URL or host/port fields."""
    full_url = (os.getenv("MODULE09_CELERY_REDIS_URL") or "").strip()
    if full_url:
        return full_url

    host = (os.getenv("MODULE09_REDIS_HOST") or "localhost").strip() or "localhost"
    port = (os.getenv("MODULE09_REDIS_PORT") or "6379").strip() or "6379"
    db = (os.getenv("MODULE09_REDIS_DB") or "0").strip() or "0"
    password = (os.getenv("MODULE09_REDIS_PASSWORD") or "").strip()

    if password:
        return f"redis://:{password}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"


def _get_celery_app():
    """Lazily create Celery app to avoid hard dependency at import time."""
    global _CELERY_APP
    if _CELERY_APP is not None:
        return _CELERY_APP
    _load_env()
    try:
        from celery import Celery
    except ImportError:
        return None
    redis_url = _redis_url_from_env()
    app = Celery(
        "module09_celery_banking",
        broker=redis_url,
        backend=redis_url,
    )
    app.conf.task_default_queue = "module09_banking_tasks"
    _CELERY_APP = app
    return _CELERY_APP


# Exported for Celery worker CLI: `celery -A function_tools_agent.function_tools:celery_app worker ...`
celery_app = _get_celery_app()


def reset_long_running_state() -> None:
    """Reset in-memory approval tickets for repeatable CLI demos."""
    _PENDING_APPROVALS.clear()


def _compute_deposit_recalc_payload(customer_id: str) -> dict[str, Any]:
    """Pure business logic used by Celery worker task."""
    retail = get_retail_deposit_snapshot(customer_id)
    if "error" in retail:
        return {"status": "error", "error": retail["error"], "customer_id": customer_id.strip().upper()}
    score = (
        45
        + (20 if retail["cash_deposit_share"] < 0.20 else 5)
        + (20 if retail["avg_month_end_balance"] > 100_000 else 8)
        + (15 if retail["deposit_count"] >= 4 else 5)
    )
    return {
        "status": "completed",
        "customer_id": retail["customer_id"],
        "customer_name": retail["customer_name"],
        "deposit_stability_score": min(score, 100),
        "recommended_action": "Offer premium renewal campaign" if score >= 75 else "Keep on standard growth journey",
    }


if celery_app is not None:

    @celery_app.task(name="module09.recalc_deposit_score")
    def recalc_deposit_score_task(task_customer_id: str) -> dict[str, Any]:
        """Celery worker task: compute deposit recalc payload."""
        return _compute_deposit_recalc_payload(task_customer_id)


def get_retail_deposit_snapshot(customer_id: str) -> dict[str, Any]:
    """Return a compact retail deposit snapshot from Module 08 tools."""
    profile = get_deposit_profile(customer_id)
    if "error" in profile:
        return profile
    deposits = get_recent_deposits(customer_id)
    if "error" in deposits:
        return deposits
    return {
        "status": "success",
        "customer_id": profile["customer_id"],
        "customer_name": profile["customer_name"],
        "segment": profile["segment"],
        "monthly_income": profile["monthly_income"],
        "avg_month_end_balance": profile["avg_month_end_balance"],
        "deposit_count": deposits["deposit_count"],
        "total_deposit_amount": deposits["total_deposit_amount"],
        "cash_deposit_share": deposits["cash_deposit_share"],
    }


def get_business_overdraft_snapshot(customer_id: str) -> dict[str, Any]:
    """Return a compact business-banking snapshot from Module 07 tools."""
    deposits = get_monthly_deposits(customer_id)
    if "error" in deposits:
        return deposits
    overdraft = get_overdraft_request(customer_id)
    if "error" in overdraft:
        return overdraft
    return {
        "status": "success",
        "customer_id": overdraft["customer_id"],
        "customer_name": overdraft["customer_name"],
        "deposit_count": deposits["deposit_count"],
        "total_deposits": deposits["total_deposits"],
        "average_deposit": deposits["average_deposit"],
        "current_balance": overdraft["current_balance"],
        "overdraft_limit_requested": overdraft["overdraft_limit_requested"],
        "demo_expected_decision": overdraft["demo_expected_decision"],
    }


def submit_deposit_recalc_task(customer_id: str) -> dict[str, Any]:
    """Enqueue async deposit score recalculation via Celery (Redis broker)."""
    app = _get_celery_app()
    normalized = customer_id.strip().upper()
    if app is None:
        return {
            "status": "error",
            "customer_id": normalized,
            "message": "Celery is not installed. Install with: pip install 'celery[redis]'",
        }

    try:
        task = recalc_deposit_score_task.delay(normalized)
    except Exception as exc:  # pragma: no cover - runtime env dependent
        return {
            "status": "error",
            "customer_id": normalized,
            "message": f"Celery broker/backend unavailable: {exc}",
        }
    return {
        "status": "queued",
        "customer_id": normalized,
        "task_id": task.id,
        "message": "Task queued. Call get_deposit_recalc_task_status(task_id) to check progress.",
    }


def get_deposit_recalc_task_status(task_id: str) -> dict[str, Any]:
    """Fetch Celery task status/result for a previously submitted task."""
    app = _get_celery_app()
    if app is None:
        return {
            "status": "error",
            "task_id": task_id,
            "message": "Celery is not installed. Install with: pip install 'celery[redis]'",
        }
    try:
        result = app.AsyncResult(task_id)
    except Exception as exc:  # pragma: no cover - runtime env dependent
        return {"status": "error", "task_id": task_id, "message": f"Unable to query task status: {exc}"}

    payload: dict[str, Any] = {
        "task_id": task_id,
        "state": str(result.state),
        "ready": bool(result.ready()),
        "successful": bool(result.successful()) if result.ready() else False,
    }
    info = getattr(result, "info", None)
    if isinstance(info, dict):
        if "progress_pct" in info:
            payload["progress_pct"] = info.get("progress_pct")
        if "stage" in info:
            payload["stage"] = info.get("stage")
    if result.ready():
        if result.successful():
            payload["result"] = result.result
        else:
            payload["error"] = str(result.result)
    return payload


def ask_for_exception_clearance(customer_id: str, reason: str) -> dict[str, Any]:
    """Long-running starter tool: create a manual approval ticket and return pending."""
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    _PENDING_APPROVALS[ticket_id] = {
        "customer_id": customer_id.strip().upper(),
        "reason": reason.strip(),
    }
    return {
        "status": "pending",
        "ticket_id": ticket_id,
        "customer_id": customer_id.strip().upper(),
        "message": "Manual approval requested. Awaiting operations decision.",
    }


def apply_exception_clearance(customer_id: str, ticket_id: str) -> dict[str, Any]:
    """Finalize a pending ticket after approval is received."""
    normalized_ticket = ticket_id.strip().upper()
    payload = _PENDING_APPROVALS.pop(normalized_ticket, None)
    if not payload:
        return {
            "status": "not_found",
            "ticket_id": normalized_ticket,
            "message": "Ticket does not exist or is already processed.",
        }
    return {
        "status": "approved",
        "ticket_id": normalized_ticket,
        "customer_id": customer_id.strip().upper(),
        "reason": payload["reason"],
        "message": "Exception clearance applied successfully.",
    }

