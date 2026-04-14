"""Module 26: Sequential retail deposit workflow with JSON decision output."""

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

MIN_RETAIL_DEPOSIT_TOKENS = 1200


def _build_llm(settings: Settings) -> LiteLlm:
    return LiteLlm(
        model=settings.litellm_model,
        api_base=settings.api_base,
        api_key=settings.api_key,
        max_tokens=max(settings.max_tokens, MIN_RETAIL_DEPOSIT_TOKENS),
    )


def create_agent(settings: Settings | None = None) -> SequentialAgent:
    resolved = settings or get_settings()
    llm = _build_llm(resolved)

    intake_agent = LlmAgent(
        name="deposit_intake_agent",
        model=llm,
        description="Collects customer profile and deposit behavior for intake.",
        instruction=(
            "You are a retail deposit onboarding analyst.\n"
            "The user message contains a customer ID.\n"
            "You MUST call both tools before writing your output:\n"
            "1) get_deposit_profile(customer_id)\n"
            "2) get_recent_deposits(customer_id)\n"
            "Return a short markdown section titled '## Intake Summary' with:\n"
            "- customer name and segment\n"
            "- monthly income and average month-end balance\n"
            "- deposit count, total deposit amount, and cash deposit share\n"
            "- intake status as READY or NEEDS_REVIEW."
        ),
        tools=[get_deposit_profile, get_recent_deposits],
        output_key="deposit_intake_summary",
    )

    risk_agent = LlmAgent(
        name="deposit_risk_agent",
        model=llm,
        description="Performs AML and velocity checks for retail deposit risk.",
        instruction=(
            "You are a compliance and fraud risk specialist.\n"
            "The user message contains a customer ID.\n"
            "You MUST call both tools before writing your output:\n"
            "1) run_aml_screening(customer_id)\n"
            "2) run_velocity_check(customer_id)\n"
            "Return a short markdown section titled '## Risk Summary' with:\n"
            "- aml_status and aml_alerts_90d\n"
            "- velocity_status and high_velocity_days_30d\n"
            "- risk_level as LOW, MEDIUM, or HIGH\n"
            "- a one-line risk recommendation."
        ),
        tools=[run_aml_screening, run_velocity_check],
        output_key="deposit_risk_summary",
    )

    decision_agent = LlmAgent(
        name="deposit_decision_agent",
        model=llm,
        description="Builds final workflow decision payload as strict JSON.",
        instruction=(
            "You are the retail deposit workflow decision API agent.\n"
            "The user message contains a customer ID.\n"
            "First call get_deposit_offer_request(customer_id).\n\n"
            "Then read prior sequential outputs from session state:\n"
            "- Intake summary: {deposit_intake_summary}\n"
            "- Risk summary: {deposit_risk_summary}\n\n"
            "Return ONLY valid JSON (no markdown, no code fences, no extra text).\n"
            "Use this exact schema:\n"
            "{\n"
            '  "customer_id": "string",\n'
            '  "customer_name": "string",\n'
            '  "workflow": "retail_deposit_sequential_v1",\n'
            '  "status": "APPROVED|CONDITIONAL|REVIEW_REQUIRED",\n'
            '  "recommended_offer": "string",\n'
            '  "requested_offer": "string",\n'
            '  "risk_level": "LOW|MEDIUM|HIGH",\n'
            '  "decision_summary": "string",\n'
            '  "next_actions": ["string", "string"],\n'
            '  "evidence": {\n'
            '    "intake_summary": "string",\n'
            '    "risk_summary": "string"\n'
            "  }\n"
            "}\n\n"
            "If demo_expected_offer is SAFE_GROWTH set status to REVIEW_REQUIRED.\n"
            "If demo_expected_offer is PREMIUM_PLUS set status to APPROVED.\n"
            "recommended_offer must match demo_expected_offer."
        ),
        tools=[get_deposit_offer_request],
        output_key="deposit_workflow_json",
    )

    return SequentialAgent(
        name="retail_deposit_workflow_sequential",
        description=(
            "Module 26: Sequential retail deposit workflow pipeline for API output. "
            "Runs intake, risk, and decision stages and returns strict JSON."
        ),
        sub_agents=[intake_agent, risk_agent, decision_agent],
    )
