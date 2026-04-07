from __future__ import annotations

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from simple_litellm_agent.config import Settings, get_settings

MIN_MULTI_AGENT_TOKENS = 160


def _build_model(settings: Settings) -> LiteLlm:
    return LiteLlm(
        model=settings.litellm_model,
        api_base=settings.api_base,
        api_key=settings.api_key,
        max_tokens=max(settings.max_tokens, MIN_MULTI_AGENT_TOKENS),
    )


def create_writer_agent(settings: Settings | None = None) -> Agent:
    resolved_settings = settings or get_settings()

    return Agent(
        name="writer_agent",
        description="Writes exactly 2 short paragraphs for the topic from chat.",
        instruction=(
            "You are a simple writing agent for a beginner ADK lesson. "
            "When the user gives a topic, respond with exactly 2 short paragraphs. "
            "Do not use headings, bullet points, or extra notes."
        ),
        model=_build_model(resolved_settings),
    )


def create_bullet_agent(settings: Settings | None = None) -> Agent:
    resolved_settings = settings or get_settings()

    return Agent(
        name="bullet_agent",
        description="Returns exactly 3 bullet points for the topic from chat.",
        instruction=(
            "You are a simple summarizer agent for a beginner ADK lesson. "
            "When the user gives a topic, respond with exactly 3 concise bullet points. "
            "Each bullet must start with '- '."
        ),
        model=_build_model(resolved_settings),
    )


