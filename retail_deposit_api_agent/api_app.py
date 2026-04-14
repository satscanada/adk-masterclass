"""Standalone FastAPI app for Module 26 retail deposit workflow."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .main import run_prompt


class ChatPayload(BaseModel):
    prompt: str = Field(..., description="Retail customer ID (for example RET-3101).")
    user_id: str = Field(default="module26-user", description="Stable user id for multi-turn sessions.")
    session_id: str | None = Field(default=None, description="Optional session id to continue a conversation.")


class ChatResponse(BaseModel):
    agent_key: str
    session_id: str
    response: str


app = FastAPI(
    title="Module 26 Retail Deposit API",
    description="Standalone API wrapper for the sequential retail deposit workflow agent.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def run_retail_deposit_chat(payload: ChatPayload) -> ChatResponse:
    clean_prompt = payload.prompt.strip()
    if not clean_prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    session_id = payload.session_id or str(uuid.uuid4())

    try:
        response = run_prompt(
            clean_prompt,
            user_id=payload.user_id.strip() or "module26-user",
            session_id=session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        agent_key="retail_deposit_api_agent",
        session_id=session_id,
        response=response,
    )
