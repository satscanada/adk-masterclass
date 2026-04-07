from __future__ import annotations

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from simple_litellm_agent.config import Settings, get_settings

MIN_STREAMING_TOKENS = 256

STREAMING_INSTRUCTION = (
    "You are helpful. Always respond with at least 3 sentences. "
    "Keep a friendly, clear tone suitable for a beginner audience."
)


def create_agent(settings: Settings | None = None) -> Agent:
    resolved = settings or get_settings()

    return Agent(
        name="streaming_agent",
        description=(
            "Streams token-by-token replies through ADK's event loop for Module 04. "
            "Uses the same LiteLLM-backed model as the single-agent lesson."
        ),
        instruction=STREAMING_INSTRUCTION,
        model=LiteLlm(
            model=resolved.litellm_model,
            api_base=resolved.api_base,
            api_key=resolved.api_key,
            max_tokens=max(resolved.max_tokens, MIN_STREAMING_TOKENS),
        ),
    )
