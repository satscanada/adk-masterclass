"""Module 08: Workflow agents for retail deposit processing."""

from __future__ import annotations

from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm

from simple_litellm_agent.config import Settings, get_settings

from .workflow_tools import (
    clear_deposit_exception,
    fetch_next_deposit_exception,
    get_deposit_offer_request,
    get_deposit_profile,
    get_recent_deposits,
    run_aml_screening,
    run_velocity_check,
)

MIN_WORKFLOW_TOKENS = 1024


def _build_llm(settings: Settings) -> LiteLlm:
    return LiteLlm(
        model=settings.litellm_model,
        api_base=settings.api_base,
        api_key=settings.api_key,
        max_tokens=max(settings.max_tokens, MIN_WORKFLOW_TOKENS),
    )


def _build_loop_agent(llm: LiteLlm) -> LoopAgent:
    exception_resolver = LlmAgent(
        name="exception_resolver_agent",
        model=llm,
        description="Resolves deposit processing exceptions one item at a time.",
        instruction=(
            "You are an operations specialist in a retail core banking deposit platform.\n"
            "The user message is a customer ID.\n"
            "1. Call fetch_next_deposit_exception(customer_id).\n"
            "2. If has_more is false, output: 'No pending exception to clear in this cycle.'\n"
            "3. If has_more is true, read pending_item.reference_id and call "
            "clear_deposit_exception(customer_id, reference_id).\n"
            "4. Output a short markdown note with: reference, issue, and action taken.\n"
            "Keep output concise and factual."
        ),
        tools=[fetch_next_deposit_exception, clear_deposit_exception],
        output_key="loop_last_resolution",
    )
    return LoopAgent(
        name="deposit_exception_loop",
        description=(
            "Module 08: LoopAgent use case. Replays exception-resolution cycles for "
            "retail deposit posting and reconciliation."
        ),
        sub_agents=[exception_resolver],
        max_iterations=3,
    )


def _build_parallel_agent(llm: LiteLlm) -> ParallelAgent:
    deposit_health_agent = LlmAgent(
        name="deposit_health_agent",
        model=llm,
        description="Analyzes inbound deposit behavior and liquidity quality.",
        instruction=(
            "You are a deposit growth analyst.\n"
            "The user message is a customer ID.\n"
            "Call get_deposit_profile and get_recent_deposits before writing anything.\n"
            "Return a markdown section titled '## Deposit Health Snapshot' with:\n"
            "- deposit count and total\n"
            "- average deposit\n"
            "- cash deposit share\n"
            "- liquidity grade (strong/moderate/weak)"
        ),
        tools=[get_deposit_profile, get_recent_deposits],
        output_key="parallel_deposit_health",
    )

    compliance_risk_agent = LlmAgent(
        name="compliance_risk_agent",
        model=llm,
        description="Assesses AML and transaction velocity risk in parallel.",
        instruction=(
            "You are a compliance risk analyst.\n"
            "The user message is a customer ID.\n"
            "Call run_aml_screening and run_velocity_check before writing.\n"
            "Return a markdown section titled '## Risk & Compliance Snapshot' with:\n"
            "- AML status with alert count\n"
            "- velocity status with count of high-velocity days\n"
            "- risk tier (low/medium/high)\n"
            "- one-line recommendation"
        ),
        tools=[run_aml_screening, run_velocity_check],
        output_key="parallel_risk_snapshot",
    )

    return ParallelAgent(
        name="deposit_parallel_assessment",
        description=(
            "Module 08: ParallelAgent use case. Runs deposit-health and compliance "
            "analysis concurrently for faster retail onboarding decisions."
        ),
        sub_agents=[deposit_health_agent, compliance_risk_agent],
    )


def _build_composition_agent(llm: LiteLlm) -> SequentialAgent:
    parallel_assessment = _build_parallel_agent(llm)
    reconciliation_loop = _build_loop_agent(llm)

    final_offer_agent = LlmAgent(
        name="final_offer_agent",
        model=llm,
        description="Produces final deposit product recommendation from workflow outputs.",
        instruction=(
            "You are a retail deposit product decision manager.\n"
            "The user message is a customer ID.\n"
            "Call get_deposit_offer_request first.\n\n"
            "Read these workflow outputs from session state:\n"
            "- parallel_deposit_health: {parallel_deposit_health}\n"
            "- parallel_risk_snapshot: {parallel_risk_snapshot}\n"
            "- loop_last_resolution: {loop_last_resolution}\n\n"
            "Mandatory: response field 'Recommended Offer' must exactly match "
            "demo_expected_offer from the tool for this teaching dataset.\n"
            "Do not invent AML alerts, velocity spikes, or risk tiers that contradict "
            "the Risk & Compliance Snapshot and tool outputs.\n\n"
            "Return markdown titled '## Final Deposit Offer Decision' containing:\n"
            "1. Recommended Offer\n"
            "2. Why this offer fits (3 bullets)\n"
            "3. Operational next step\n"
            "4. Customer communication note"
        ),
        tools=[get_deposit_offer_request],
        output_key="final_offer_decision",
    )

    return SequentialAgent(
        name="retail_deposit_composition",
        description=(
            "Module 08: Composition pattern. Sequentially executes a ParallelAgent fan-out, "
            "then a LoopAgent reconciliation cycle, then a final decision LlmAgent."
        ),
        sub_agents=[parallel_assessment, reconciliation_loop, final_offer_agent],
    )


def create_loop_agent(settings: Settings | None = None) -> LoopAgent:
    resolved = settings or get_settings()
    llm = _build_llm(resolved)
    return _build_loop_agent(llm)


def create_parallel_agent(settings: Settings | None = None) -> ParallelAgent:
    resolved = settings or get_settings()
    llm = _build_llm(resolved)
    return _build_parallel_agent(llm)


def create_composition_agent(settings: Settings | None = None) -> SequentialAgent:
    resolved = settings or get_settings()
    llm = _build_llm(resolved)
    return _build_composition_agent(llm)

