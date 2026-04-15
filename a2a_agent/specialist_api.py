"""Remote fixed-income specialist for Module 12 A2A lesson."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

_TASKS: dict[str, dict[str, Any]] = {}


class TaskCreatePayload(BaseModel):
    goal: str = Field(..., description="Delegation goal from local banking assistant.")
    context: dict[str, Any] = Field(default_factory=dict, description="Customer ladder-planning inputs.")


def _build_ladder_artifact(context: dict[str, Any]) -> dict[str, Any]:
    available_cash = float(context.get("available_cash", 0))
    horizon_years = int(context.get("time_horizon_years", 5) or 5)
    needs_liquidity = bool(context.get("needs_periodic_liquidity", True))
    auto_roll = str(context.get("auto_roll_preference", "auto_roll_best_rate")).strip() or "auto_roll_best_rate"

    # Keep the module's teaching ladder bounded and predictable.
    rung_count = max(3, min(5, horizon_years))
    terms = list(range(1, rung_count + 1))
    per_rung = round(available_cash / rung_count, 2) if rung_count else available_cash

    # Mock APY curve: gradual slope across longer maturities.
    base_apy = 3.90
    apy_step = 0.18
    rungs = []
    for idx, term_years in enumerate(terms):
        apy = round(base_apy + (idx * apy_step), 2)
        action = "auto_roll" if auto_roll != "return_cash" else "return_cash"
        rungs.append(
            {
                "rung_index": idx + 1,
                "term_years": term_years,
                "allocation_usd": per_rung,
                "target_apy_percent": apy,
                "maturity_action": action,
            }
        )

    if needs_liquidity:
        liquidity_note = "One rung matures each year to preserve access windows."
    else:
        liquidity_note = "Liquidity is deprioritized; maximize blended APY across longer terms."

    return {
        "plan_id": f"ladder-{uuid.uuid4().hex[:10]}",
        "strategy": f"{terms[0]}y-{terms[-1]}y annual ladder",
        "rungs": rungs,
        "blended_target_apy_percent": round(sum(r["target_apy_percent"] for r in rungs) / len(rungs), 2),
        "liquidity_note": liquidity_note,
        "review_windows": [
            "Review each rung 30 days before maturity.",
            "Compare brokered and branch CD rates before grace periods close.",
        ],
    }


def _task_snapshot(task: dict[str, Any]) -> dict[str, Any]:
    elapsed = time.monotonic() - float(task["created_monotonic"])
    if elapsed < 0.35:
        status = "queued"
        progress_message = "Task accepted. Validating Agent Card and ladder constraints."
    elif elapsed < 0.9:
        status = "running"
        progress_message = "Evaluating staggered maturities, APY spread, and rollover policy."
    else:
        status = "completed"
        progress_message = "Ladder construction complete."

    response: dict[str, Any] = {
        "task_id": task["task_id"],
        "status": status,
        "progress_message": progress_message,
    }
    if status == "completed":
        response["artifact"] = task["artifact"]
    return response


app = FastAPI(
    title="Module 12 Fixed-Income Specialist (A2A peer)",
    description="Remote A2A peer that builds CD ladder artifacts for delegated planning tasks.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/.well-known/agent-card")
def get_agent_card() -> dict[str, Any]:
    return {
        "agent_name": "fixed_income_specialist",
        "version": "1.0.0",
        "description": "Remote specialist for CD ladder structuring and maturity scheduling.",
        "capabilities": {
            "supports_ladder_types": ["annual_3_rung", "annual_4_rung", "annual_5_rung"],
            "supports_periodic_liquidity": True,
            "supports_auto_roll_policies": ["auto_roll_best_rate", "return_cash", "mixed"],
            "outputs": ["ladder_plan_artifact"],
        },
        "auth": {"type": "none", "notes": "Demo mode for local learning."},
        "endpoints": {
            "create_task": "/a2a/tasks",
            "get_task": "/a2a/tasks/{task_id}",
        },
    }


@app.post("/a2a/tasks")
def create_task(payload: TaskCreatePayload) -> dict[str, Any]:
    goal = payload.goal.strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal must not be empty.")

    task_id = f"task-{uuid.uuid4().hex[:12]}"
    artifact = _build_ladder_artifact(payload.context)
    _TASKS[task_id] = {
        "task_id": task_id,
        "goal": goal,
        "context": payload.context,
        "artifact": artifact,
        "created_monotonic": time.monotonic(),
    }
    return {
        "task_id": task_id,
        "status": "queued",
    }


@app.get("/a2a/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, Any]:
    task = _TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Unknown task_id '{task_id}'.")
    return _task_snapshot(task)

