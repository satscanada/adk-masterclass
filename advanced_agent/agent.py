from __future__ import annotations

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from simple_litellm_agent.config import Settings, get_settings

from .weather_tools import celsius_to_fahrenheit_display, fetch_current_weather

MIN_TOOL_AGENT_TOKENS = 512

WEATHER_AGENT_INSTRUCTION = """You are a weather-only assistant.

Scope:
- Answer only questions about weather, temperature, conditions, forecast-style questions,
  wind, precipitation, or climate for a specific place.
- If the user asks about anything else (general knowledge, code, jokes, math unrelated to
  weather, etc.), reply with exactly this sentence and do not call any tools:
  "I only answer weather questions. Ask me about the weather for a place (use a place id like calgary, london, or paris)."

When the question is in scope:
1. Infer the Meteosource place_id from the user's message (use a short lowercase slug such as
   calgary, new_york, london, tokyo). The place_id is what we pass to the API.
2. Call fetch_current_weather(place_id) to load conditions.
3. Call celsius_to_fahrenheit_display with the temperature_celsius value from that result so you
   can report both Celsius and Fahrenheit.
4. In your final answer, include: the conditions summary, temperatures in °C and °F (using the
   conversion tool output), and briefly mention wind or precipitation when the tool returned them.

Never invent temperatures; always use the tools for real places."""

WEATHER_AGENT_DESCRIPTION = (
    "Module 05: weather assistant using Meteosource (free tier) and explicit temperature "
    "conversion. Refuses non-weather questions with a fixed message."
)


def create_agent(settings: Settings | None = None) -> Agent:
    resolved = settings or get_settings()

    return Agent(
        name="weather_assistant",
        description=WEATHER_AGENT_DESCRIPTION,
        instruction=WEATHER_AGENT_INSTRUCTION,
        tools=[fetch_current_weather, celsius_to_fahrenheit_display],
        output_key="last_weather_reply",
        model=LiteLlm(
            model=resolved.litellm_model,
            api_base=resolved.api_base,
            api_key=resolved.api_key,
            max_tokens=max(resolved.max_tokens, MIN_TOOL_AGENT_TOKENS),
        ),
    )
