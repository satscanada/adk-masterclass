from __future__ import annotations

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from .config import Settings, get_settings


def create_agent(settings: Settings | None = None) -> Agent:
    settings = settings or get_settings()

    return Agent(
        name="root_agent",
        description="A tiny Google ADK agent that calls a LiteLLM-compatible chat completions endpoint.",
        instruction=settings.agent_instruction,
        model=LiteLlm(
            model=settings.litellm_model,
            api_base=settings.api_base,
            api_key=settings.api_key,
            max_tokens=settings.max_tokens,
        ),
    )

