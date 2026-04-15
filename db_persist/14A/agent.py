"""Module 14A agent graph: spending log stage + deterministic coaching stage."""

from __future__ import annotations

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm

from simple_litellm_agent.config import Settings, get_settings

from .tools import (
    append_spending_snapshot,
    check_trend_and_suppression,
    get_weekly_transactions,
    record_suggestion_response,
)

MIN_SPENDING_COACH_TOKENS = 1024


def _build_llm(settings: Settings) -> LiteLlm:
    return LiteLlm(
        model=settings.litellm_model,
        api_base=settings.api_base,
        api_key=settings.api_key,
        max_tokens=max(settings.max_tokens, MIN_SPENDING_COACH_TOKENS),
    )


def create_agent(settings: Settings | None = None) -> SequentialAgent:
    resolved = settings or get_settings()
    llm = _build_llm(resolved)

    log_agent = LlmAgent(
        name="spending_log_agent",
        model=llm,
        description="Fetches weekly spend snapshot and appends it to persistent state.",
        instruction=(
            "You are a spending-log assistant for Module 14A.\n"
            "The prompt includes `customer_id`.\n"
            "Always call both tools in this order:\n"
            "1) get_weekly_transactions(customer_id)\n"
            "2) append_spending_snapshot(customer_id, week, category, amount)\n"
            "Use week/category/amount from the first tool result.\n"
            "Return markdown titled '## Spending Log Update' with:\n"
            "- latest week and category\n"
            "- latest amount\n"
            "- log length for this customer."
        ),
        tools=[get_weekly_transactions, append_spending_snapshot],
        output_key="spending_log_update",
    )

    coaching_agent = LlmAgent(
        name="spending_coaching_agent",
        model=llm,
        description="Reads trend + suppression guard and frames customer coaching.",
        instruction=(
            "You are a retail spending coach.\n"
            "First read previous stage summary: {spending_log_update}\n"
            "Then call check_trend_and_suppression(customer_id).\n"
            "Rules:\n"
            "- If trend_detected is false: return neutral acknowledgement, no suggestion.\n"
            "- If trend_detected is true and suppressed is true: explain cooling window.\n"
            "- If trend_detected is true and suppressed is false: provide one concise suggestion.\n"
            "The prompt may include `customer_response` as accepted/declined/not_now.\n"
            "Only when customer_response is present and trend_detected is true, "
            "call record_suggestion_response(customer_id, category, customer_response).\n"
            "Return markdown titled '## Spending Coach Result' with:\n"
            "- trend status\n"
            "- suppression status\n"
            "- coaching message."
        ),
        tools=[check_trend_and_suppression, record_suggestion_response],
        output_key="spending_coach_result",
    )

    return SequentialAgent(
        name="module14a_spending_pattern_coach",
        description=(
            "Module 14A: persistent spending pattern coach with deterministic suppression logic."
        ),
        sub_agents=[log_agent, coaching_agent],
    )
