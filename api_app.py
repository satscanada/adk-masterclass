from __future__ import annotations

import json
import logging
import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent_registry import ChatRequest, get_agent, list_agents


def _configure_advanced_agent_logging() -> None:
    """So Meteosource + reply-source INFO lines show in the API server console."""
    root = logging.getLogger("advanced_agent")
    root.setLevel(logging.INFO)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(levelname)s %(name)s: %(message)s"),
        )
        root.addHandler(handler)
    root.propagate = False


_configure_advanced_agent_logging()


class SuggestionItem(BaseModel):
    label: str
    prompt: str


class AgentSummary(BaseModel):
    key: str
    title: str
    description: str
    prompt_hint: str
    supports_streaming: bool = False
    suggestions: list[SuggestionItem] = []


class AgentListResponse(BaseModel):
    agents: list[AgentSummary]


class ChatPayload(BaseModel):
    agent_key: str = Field(..., description="The agent key from agents.json.")
    prompt: str = Field(..., description="The user message to send to the selected agent.")
    user_id: str = Field(default="api-user", description="Stable user id for multi-turn sessions.")
    session_id: str | None = Field(default=None, description="Optional session id to continue a conversation.")


class ChatResponse(BaseModel):
    agent_key: str
    agent_title: str
    session_id: str
    response: str


def _get_cors_origins() -> list[str]:
    raw_value = os.getenv(
        "AGENT_API_CORS_ORIGINS",
        "http://localhost:8513,http://127.0.0.1:8513",
    ).strip()
    if raw_value == "*":
        return ["*"]
    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    return origins or ["http://localhost:8513", "http://127.0.0.1:8513"]


app = FastAPI(
    title="ADK Agent API",
    description="HTTP wrapper around the learning-project agents.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/agents", response_model=AgentListResponse)
def read_agents() -> AgentListResponse:
    agents = [
        AgentSummary(
            key=agent.key,
            title=agent.title,
            description=agent.description,
            prompt_hint=agent.prompt_hint,
            supports_streaming=agent.supports_streaming,
            suggestions=[
                SuggestionItem(label=s.label, prompt=s.prompt)
                for s in agent.suggestions
            ],
        )
        for agent in list_agents()
    ]
    return AgentListResponse(agents=agents)


@app.post("/api/chat", response_model=ChatResponse)
def run_agent_chat(payload: ChatPayload) -> ChatResponse:
    clean_prompt = payload.prompt.strip()
    if not clean_prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    try:
        agent = get_agent(payload.agent_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    session_id = payload.session_id or str(uuid.uuid4())

    try:
        response = agent.run(
            ChatRequest(
                prompt=clean_prompt,
                user_id=payload.user_id.strip() or "api-user",
                session_id=session_id,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        agent_key=agent.key,
        agent_title=agent.title,
        session_id=session_id,
        response=response,
    )


@app.post("/api/chat/stream")
async def run_agent_chat_stream(payload: ChatPayload) -> StreamingResponse:
    clean_prompt = payload.prompt.strip()
    if not clean_prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    try:
        agent = get_agent(payload.agent_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not agent.supports_streaming or agent.stream is None:
        raise HTTPException(
            status_code=400,
            detail="This agent does not support streaming. Use POST /api/chat instead.",
        )

    session_id = payload.session_id or str(uuid.uuid4())
    request = ChatRequest(
        prompt=clean_prompt,
        user_id=payload.user_id.strip() or "api-user",
        session_id=session_id,
    )

    audit_prefix = "\x00AUDIT:"

    async def ndjson_chunks():
        try:
            async for text in agent.stream(request):
                if text.startswith(audit_prefix):
                    try:
                        audit_payload = json.loads(text[len(audit_prefix):])
                        line = json.dumps({"type": "audit", **audit_payload}) + "\n"
                    except (json.JSONDecodeError, TypeError):
                        continue
                else:
                    line = json.dumps({"type": "delta", "text": text}) + "\n"
                yield line.encode("utf-8")
            done = json.dumps(
                {
                    "type": "done",
                    "agent_key": agent.key,
                    "agent_title": agent.title,
                    "session_id": session_id,
                }
            ) + "\n"
            yield done.encode("utf-8")
        except Exception as exc:  # noqa: BLE001
            err = json.dumps({"type": "error", "detail": str(exc)}) + "\n"
            yield err.encode("utf-8")

    return StreamingResponse(ndjson_chunks(), media_type="application/x-ndjson")
