"""Module 14A agent graph: spending log stage + deterministic coaching stage."""

from __future__ import annotations

import os

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm

from simple_litellm_agent.config import Settings, get_settings

from .tools import (
    append_spending_snapshot,
    check_trend_and_suppression,
    get_weekly_transactions,
    get_weekly_transactions_with_input,
    record_suggestion_response,
)

# Minimum token budget for this module's coaching response.
# spending_log_agent produces ~100-150 tokens (tool calls + brief confirmation).
# spending_coaching_agent produces ~200-350 tokens (guard tool + coaching markdown).
# 512 is comfortable for both and keeps latency low on Sonnet-class models.
# Override with MODULE14A_MAX_TOKENS in .env for a different value.
_DEFAULT_MODULE_MAX_TOKENS = 512


def _module_max_tokens(settings: Settings) -> int:
    """Return max_tokens for Module 14A LLM calls.

    Priority order:
      1. MODULE14A_MAX_TOKENS env var (module-specific override)
      2. LITELLM_MAX_TOKENS (global, from settings) when >= _DEFAULT_MODULE_MAX_TOKENS
      3. _DEFAULT_MODULE_MAX_TOKENS (512) — floor that prevents under-sized responses
    """
    env_val = os.environ.get("MODULE14A_MAX_TOKENS", "").strip()
    if env_val:
        try:
            parsed = int(env_val)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return max(settings.max_tokens, _DEFAULT_MODULE_MAX_TOKENS)


def _build_llm(settings: Settings) -> LiteLlm:
    return LiteLlm(
        model=settings.litellm_model,
        api_base=settings.api_base,
        api_key=settings.api_key,
        max_tokens=_module_max_tokens(settings),
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
            "The prompt may optionally include `week`, `category`, and `amount`.\n"
            "Always call both tools in this order:\n"
            "1) get_weekly_transactions_with_input(customer_id, week?, category?, amount?)\n"
            "2) append_spending_snapshot(customer_id, week, category, amount)\n"
            "Use week/category/amount from the first tool result.\n"
            "If week/category/amount are provided in the prompt, pass them to the first tool.\n"
            "If not provided, call the first tool with only customer_id for deterministic mock progression.\n"
            "Return markdown titled '## Spending Log Update' with:\n"
            "- latest week and category\n"
            "- latest amount\n"
            "- log length for this customer."
        ),
        tools=[get_weekly_transactions_with_input, get_weekly_transactions, append_spending_snapshot],
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
