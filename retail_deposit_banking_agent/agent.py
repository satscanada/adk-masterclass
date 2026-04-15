"""Module 13: simple retail deposit banking SequentialAgent use case."""

from __future__ import annotations

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm

from simple_litellm_agent.config import Settings, get_settings
from workflow_agent.workflow_tools import (
    get_deposit_offer_request,
    get_deposit_profile,
    get_recent_deposits,
    run_aml_screening,
    run_velocity_check,
)

MIN_MODULE13_TOKENS = 900


def _build_llm(settings: Settings) -> LiteLlm:
    return LiteLlm(
        model=settings.litellm_model,
        api_base=settings.api_base,
        api_key=settings.api_key,
        max_tokens=max(settings.max_tokens, MIN_MODULE13_TOKENS),
    )


def create_agent(settings: Settings | None = None) -> SequentialAgent:
    resolved = settings or get_settings()
    llm = _build_llm(resolved)

    intake_agent = LlmAgent(
        name="retail_intake_agent",
        model=llm,
        description="Collects profile and recent deposit behavior for intake.",
        instruction=(
            "You are a retail deposit intake analyst.\n"
            "The user message contains a customer ID.\n"
            "Always call both tools before writing your response:\n"
            "1) get_deposit_profile(customer_id)\n"
            "2) get_recent_deposits(customer_id)\n"
            "Return markdown titled '## Intake Snapshot' with:\n"
            "- customer name and segment\n"
            "- monthly income and average month-end balance\n"
            "- deposit count and total deposit amount\n"
            "- cash deposit share with one-line interpretation."
        ),
        tools=[get_deposit_profile, get_recent_deposits],
        output_key="module13_intake_snapshot",
    )

    risk_agent = LlmAgent(
        name="retail_risk_agent",
        model=llm,
        description="Checks AML and transaction velocity.",
        instruction=(
            "You are a retail deposit risk analyst.\n"
            "The user message contains a customer ID.\n"
            "Always call both tools before writing your response:\n"
            "1) run_aml_screening(customer_id)\n"
            "2) run_velocity_check(customer_id)\n"
            "Return markdown titled '## Risk Snapshot' with:\n"
            "- aml_status and aml_alerts_90d\n"
            "- velocity_status and high_velocity_days_30d\n"
            "- risk level as LOW, MEDIUM, or HIGH."
        ),
        tools=[run_aml_screening, run_velocity_check],
        output_key="module13_risk_snapshot",
    )

    offer_agent = LlmAgent(
        name="retail_offer_agent",
        model=llm,
        description="Generates a simple offer recommendation and next actions.",
        instruction=(
            "You are the final retail deposit recommendation specialist.\n"
            "The user message contains a customer ID.\n"
            "First call get_deposit_offer_request(customer_id).\n"
            "Then use prior stage summaries:\n"
            "- Intake: {module13_intake_snapshot}\n"
            "- Risk: {module13_risk_snapshot}\n"
            "Return markdown titled '## Module 13 Recommendation' with:\n"
            "- Decision: APPROVE or REVIEW_REQUIRED\n"
            "- Requested offer and recommended offer\n"
            "- A short rationale\n"
            "- Next actions as exactly 2 bullet points\n"
            "Decision rule for this lesson:\n"
            "- If demo_expected_offer is PREMIUM_PLUS => APPROVE\n"
            "- If demo_expected_offer is SAFE_GROWTH => REVIEW_REQUIRED\n"
            "Recommended offer must match demo_expected_offer."
        ),
        tools=[get_deposit_offer_request],
        output_key="module13_final_recommendation",
    )

    return SequentialAgent(
        name="module13_retail_deposit_banking",
        description=(
            "Module 13: simple retail deposit banking use case with intake, risk, and offer recommendation."
        ),
        sub_agents=[intake_agent, risk_agent, offer_agent],
    )

