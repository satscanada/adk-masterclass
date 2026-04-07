from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path


@dataclass(frozen=True)
class ChatRequest:
    prompt: str
    user_id: str
    session_id: str


@dataclass(frozen=True)
class Suggestion:
    label: str
    prompt: str


@dataclass(frozen=True)
class AgentDefinition:
    key: str
    title: str
    description: str
    prompt_hint: str
    run: Callable[[ChatRequest], str]
    supports_streaming: bool
    stream: Callable[[ChatRequest], AsyncIterator[str]] | None
    suggestions: tuple[Suggestion, ...] = ()


@dataclass(frozen=True)
class AgentConfig:
    key: str
    title: str
    description: str
    prompt_hint: str
    module: str
    supports_streaming: bool
    suggestions: tuple[Suggestion, ...] = ()


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}

    def register(self, agent: AgentDefinition) -> None:
        self._agents[agent.key] = agent

    def get(self, key: str) -> AgentDefinition:
        try:
            return self._agents[key]
        except KeyError as exc:
            raise KeyError(f"Unknown agent '{key}'. Registered agents: {', '.join(sorted(self._agents))}") from exc

    def list(self) -> tuple[AgentDefinition, ...]:
        return tuple(self._agents.values())


AGENTS_FILE = Path(__file__).resolve().parent / "agents.json"
registry = AgentRegistry()


def _load_agent_configs() -> tuple[AgentConfig, ...]:
    payload = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    raw_agents = payload.get("agents", [])

    if not isinstance(raw_agents, list):
        raise ValueError("`agents.json` must contain an `agents` list.")

    configs: list[AgentConfig] = []
    for raw_agent in raw_agents:
        raw_suggestions = raw_agent.get("suggestions") or []
        suggestions = tuple(
            Suggestion(label=str(s["label"]), prompt=str(s["prompt"]))
            for s in raw_suggestions
            if isinstance(s, dict) and "label" in s and "prompt" in s
        )
        configs.append(
            AgentConfig(
                key=str(raw_agent["key"]),
                title=str(raw_agent["title"]),
                description=str(raw_agent["description"]),
                prompt_hint=str(raw_agent.get("prompt_hint", "")),
                module=str(raw_agent["module"]),
                supports_streaming=bool(raw_agent.get("supports_streaming", False)),
                suggestions=suggestions,
            )
        )
    return tuple(configs)


def _run_prompt_module(request: ChatRequest, module_name: str) -> str:
    module = import_module(module_name)
    run_prompt = getattr(module, "run_prompt")

    return run_prompt(
        request.prompt,
        user_id=request.user_id,
        session_id=request.session_id,
    )


def _build_run_function(module_name: str) -> Callable[[ChatRequest], str]:
    def _run(request: ChatRequest) -> str:
        return _run_prompt_module(request, module_name)

    return _run


def _build_stream_function(module_name: str) -> Callable[[ChatRequest], AsyncIterator[str]] | None:
    module = import_module(module_name)
    stream_fn = getattr(module, "stream_prompt", None)
    if stream_fn is None:
        return None

    async def _stream(request: ChatRequest) -> AsyncIterator[str]:
        async for chunk in stream_fn(
            request.prompt,
            user_id=request.user_id,
            session_id=request.session_id,
        ):
            yield chunk

    return _stream


def _register_agents() -> None:
    for config in _load_agent_configs():
        stream = _build_stream_function(config.module) if config.supports_streaming else None
        if config.supports_streaming and stream is None:
            raise ValueError(
                f"Agent '{config.key}' sets supports_streaming but '{config.module}' "
                "does not define async stream_prompt(...)."
            )
        registry.register(
            AgentDefinition(
                key=config.key,
                title=config.title,
                description=config.description,
                prompt_hint=config.prompt_hint,
                run=_build_run_function(config.module),
                supports_streaming=config.supports_streaming,
                stream=stream,
                suggestions=config.suggestions,
            )
        )


_register_agents()


def list_agents() -> tuple[AgentDefinition, ...]:
    return registry.list()


def get_agent(key: str) -> AgentDefinition:
    return registry.get(key)
