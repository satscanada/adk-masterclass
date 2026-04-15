"""Standalone FastAPI app for Module 14A spending coach."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from .main import _VALID_RESPONSES, _extract_customer_id, _stable_session_id, run_prompt


class ChatPayload(BaseModel):
    prompt: str = Field(
        ...,
        description="Customer ID input (for example CUST-3001) and optional response token.",
    )
    user_id: str = Field(
        default="module14a-user",
        description="Stable user ID for persistent session continuity.",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional explicit session ID. Defaults to spending-coach-<customer>.",
    )
    week: str | None = Field(
        default=None,
        description="Optional custom week override for simulation (for example 2026-W20).",
    )
    category: str | None = Field(
        default=None,
        description="Optional custom category override (for example dining, grocery, travel).",
    )
    amount: float | None = Field(
        default=None,
        description="Optional custom amount override for simulation.",
    )
    customer_response: str | None = Field(
        default=None,
        description=(
            "Customer's response to a prior coaching suggestion. "
            "One of: accepted, declined, not_now. "
            "Takes precedence over any response keyword embedded in the prompt string."
        ),
    )

    @field_validator("customer_response", mode="before")
    @classmethod
    def validate_response(cls, v: str | None) -> str | None:
        if v is None:
            return v
        norm = v.strip().lower()
        if norm not in _VALID_RESPONSES:
            raise ValueError(
                f"customer_response must be one of: {', '.join(sorted(_VALID_RESPONSES))}. "
                f"Got: {v!r}"
            )
        return norm


class ChatResponse(BaseModel):
    agent_key: str
    session_id: str
    response: str


app = FastAPI(
    title="Module 14A Spending Coach API",
    description="Standalone API wrapper for the persistent spending pattern coaching lesson.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def run_spending_chat(payload: ChatPayload) -> ChatResponse:
    clean_prompt = payload.prompt.strip()
    if not clean_prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    try:
        customer_id = _extract_customer_id(clean_prompt)
    except ValueError:
        customer_id = None
    response_session_id = payload.session_id or (
        _stable_session_id(customer_id) if customer_id else str(uuid.uuid4())
    )
    try:
        response = run_prompt(
            clean_prompt,
            user_id=payload.user_id.strip() or "module14a-user",
            session_id=payload.session_id,
            week=payload.week,
            category=payload.category,
            amount=payload.amount,
            customer_response=payload.customer_response,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        agent_key="db_persist_14a_spending_coach",
        session_id=response_session_id,
        response=response,
    )
