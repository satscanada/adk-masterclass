from __future__ import annotations

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from simple_litellm_agent.config import Settings, get_settings

MIN_ORCHESTRATOR_TOKENS = 180
SUPPORTED_AGENT_TYPES = ("explain", "bullet", "quiz")


def _build_model(settings: Settings) -> LiteLlm:
    return LiteLlm(
        model=settings.litellm_model,
        api_base=settings.api_base,
        api_key=settings.api_key,
        max_tokens=max(settings.max_tokens, MIN_ORCHESTRATOR_TOKENS),
    )


def create_explain_agent(settings: Settings | None = None) -> Agent:
    resolved_settings = settings or get_settings()

    return Agent(
        name="explain_agent",
        description="Use when agent_type is explain. Teaches a topic in a short beginner-friendly explanation.",
        instruction=(
            "You are the explain agent for Module 03. "
            "The prompt will include 'Agent type intent: explain'. "
            "Return a short, clear explanation with simple language. "
            "Do not use bullet points or quiz questions."
        ),
        model=_build_model(resolved_settings),
    )


def create_bullet_agent(settings: Settings | None = None) -> Agent:
    resolved_settings = settings or get_settings()

    return Agent(
        name="bullet_agent",
        description="Use when agent_type is bullet. Summarizes the request into exactly 3 bullet points.",
        instruction=(
            "You are the bullet agent for Module 03. "
            "The prompt will include 'Agent type intent: bullet'. "
            "Return exactly 3 concise bullet points. "
            "Each bullet must start with '- '."
        ),
        model=_build_model(resolved_settings),
    )


def create_quiz_agent(settings: Settings | None = None) -> Agent:
    resolved_settings = settings or get_settings()

    return Agent(
        name="quiz_agent",
        description="Use when agent_type is quiz. Creates exactly 3 short quiz questions from the request.",
        instruction=(
            "You are the quiz agent for Module 03. "
            "The prompt will include 'Agent type intent: quiz'. "
            "Return exactly 3 short quiz questions. "
            "Number them 1 to 3 and keep them beginner-friendly."
        ),
        model=_build_model(resolved_settings),
    )
