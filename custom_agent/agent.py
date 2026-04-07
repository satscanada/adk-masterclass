from __future__ import annotations

from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.models.lite_llm import LiteLlm
from google.adk.utils.context_utils import Aclosing
from google.genai import types

from simple_litellm_agent.config import Settings, get_settings

TECH_KEYWORDS = frozenset(
    {
        "python",
        "code",
        "api",
        "database",
        "algorithm",
        "debug",
        "javascript",
        "typescript",
        "react",
        "nodejs",
        "sql",
        "docker",
        "kubernetes",
        "git",
        "cockroachdb",
        "postgres",
        "postgresql",
        "mysql",
        "mariadb",
        "oracle",
        "sqlserver",
        "sqlite",
        "redis",
        "mongodb",
        "elasticsearch",
        "kafka",
        "rabbitmq",
        "apache",
        "apachekafka"
    }
)

MIN_ROUTER_TOKENS = 256


def user_text_for_routing_parts(parts) -> str:
    """Same normalization as KeywordRoutingAgent (for keyword `in` checks)."""
    if not parts:
        return ""
    return " ".join(
        p.text or ""
        for p in parts
        if hasattr(p, "text")
    ).lower()


def routing_banner_markdown(prompt: str) -> str:
    """Shown before the model reply so chat UIs display which LlmAgent handled the turn."""
    ut = user_text_for_routing_parts([types.Part(text=prompt)])
    is_tech = any(kw in ut for kw in TECH_KEYWORDS)
    if is_tech:
        return "**Route:** Tech specialist (`tech_specialist`) · keyword match\n\n"
    return "**Route:** General specialist (`general_specialist`) · no tech keywords matched\n\n"


def _build_llm(settings: Settings) -> LiteLlm:
    return LiteLlm(
        model=settings.litellm_model,
        api_base=settings.api_base,
        api_key=settings.api_key,
        max_tokens=max(settings.max_tokens, MIN_ROUTER_TOKENS),
    )


class KeywordRoutingAgent(BaseAgent):
    """Routes user text to tech or general LlmAgent children using keyword matching."""

    tech_agent: LlmAgent
    general_agent: LlmAgent

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        user_text = ""
        if ctx.user_content and ctx.user_content.parts:
            user_text = user_text_for_routing_parts(ctx.user_content.parts)

        is_tech = any(kw in user_text for kw in TECH_KEYWORDS)
        chosen = self.tech_agent if is_tech else self.general_agent

        async with Aclosing(chosen.run_async(ctx)) as agen:
            async for event in agen:
                yield event


def create_agent(settings: Settings | None = None) -> BaseAgent:
    resolved = settings or get_settings()

    tech_agent = LlmAgent(
        name="tech_specialist",
        description="Precise technical answers for programming and systems questions.",
        instruction=(
            "You are a senior software engineer. Give precise, concise technical answers. "
            "Prefer short paragraphs or bullet lists when they improve clarity."
        ),
        model=_build_llm(resolved),
    )
    general_agent = LlmAgent(
        name="general_specialist",
        description="Friendly explanations for everyday and non-technical topics.",
        instruction=(
            "You are a warm, clear general assistant. Explain ideas in plain language "
            "for a broad audience."
        ),
        model=_build_llm(resolved),
    )

    return KeywordRoutingAgent(
        name="keyword_routing_agent",
        description=(
            "Module 06: BaseAgent subclass that routes to a tech or general LlmAgent using "
            "keyword detection (no LLM call for routing)."
        ),
        tech_agent=tech_agent,
        general_agent=general_agent,
    )
