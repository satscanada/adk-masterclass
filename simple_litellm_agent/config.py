from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_environment() -> None:
    """Load variables from `.env` if the file exists."""
    load_dotenv(ENV_FILE, override=False)


@dataclass(frozen=True)
class Settings:
    app_name: str
    provider: str
    model: str
    api_base: str
    api_key: str
    max_tokens: int
    agent_instruction: str

    @property
    def litellm_model(self) -> str:
        return f"{self.provider}/{self.model}"


def _normalize_api_base(value: str) -> str:
    cleaned = value.strip().rstrip("/")
    if not cleaned:
        raise ValueError("LITELLM_API_BASE must not be empty.")
    if cleaned.endswith("/v1"):
        return cleaned
    return f"{cleaned}/v1"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_environment()

    provider = os.getenv("LITELLM_PROVIDER", "openai").strip() or "openai"
    model = os.getenv("LITELLM_MODEL", "gemini-3-flash-preview").strip() or "gemini-3-flash-preview"
    api_base = _normalize_api_base(os.getenv("LITELLM_API_BASE", "http://127.0.0.1:4000/v1"))
    api_key = os.getenv("LITELLM_API_KEY", "not-needed").strip() or "not-needed"
    max_tokens = int(os.getenv("LITELLM_MAX_TOKENS", "32"))
    app_name = os.getenv("ADK_APP_NAME", "simple_litellm_agent").strip() or "simple_litellm_agent"
    agent_instruction = (
            os.getenv(
                "AGENT_INSTRUCTION",
                "You are a helpful beginner demo agent built with Google ADK. "
                "Answer clearly and briefly.",
            ).strip()
            or "You are a helpful beginner demo agent built with Google ADK. Answer clearly and briefly."
    )

    return Settings(
        app_name=app_name,
        provider=provider,
        model=model,
        api_base=api_base,
        api_key=api_key,
        max_tokens=max_tokens,
        agent_instruction=agent_instruction,
    )


def reset_settings_cache() -> None:
    get_settings.cache_clear()

