"""Module 07: Multi-Agent Business Banking — overdraft approval pipeline.

Architecture (SequentialAgent pipeline):
  1. deposit_agent  — fetches deposits + balance movement → writes session.state["deposit_analysis"]
  2. bill_agent     — fetches completed + upcoming bills  → writes session.state["bill_analysis"]
  3. decision_agent — reads both analyses from state, decides overdraft approval
"""

from __future__ import annotations

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm

from simple_litellm_agent.config import Settings, get_settings

from .banking_tools import (
    get_balance_movement,
    get_completed_bills,
    get_monthly_deposits,
    get_overdraft_request,
    get_upcoming_bills,
)

MIN_BANKING_TOKENS = 1024


def _build_llm(settings: Settings) -> LiteLlm:
    return LiteLlm(
        model=settings.litellm_model,
        api_base=settings.api_base,
        api_key=settings.api_key,
        max_tokens=max(settings.max_tokens, MIN_BANKING_TOKENS),
    )


def create_agent(settings: Settings | None = None) -> SequentialAgent:
    resolved = settings or get_settings()
    llm = _build_llm(resolved)

    deposit_agent = LlmAgent(
        name="deposit_agent",
        model=llm,
        description="Analyzes customer deposit transactions and balance movement over the last month.",
        instruction=(
            "You are a bank deposit analyst. The user message contains a customer ID.\n"
            "You MUST call both tools before writing your analysis — do not skip tools or invent numbers.\n"
            "1. Call get_monthly_deposits with the customer ID to retrieve deposit transactions.\n"
            "2. Call get_balance_movement with the same customer ID to retrieve daily balance snapshots.\n"
            "3. Produce a structured analysis covering:\n"
            "   - Total deposits and deposit frequency\n"
            "   - Average deposit amount\n"
            "   - Balance trend (rising, falling, volatile)\n"
            "   - Minimum and maximum balance observed\n"
            "   - Cash-flow health assessment (strong / moderate / weak)\n"
            "Format the output as a clear markdown section titled '## Deposit & Balance Analysis'."
        ),
        tools=[get_monthly_deposits, get_balance_movement],
        output_key="deposit_analysis",
    )

    bill_agent = LlmAgent(
        name="bill_agent",
        model=llm,
        description="Analyzes customer bill payments and upcoming obligations.",
        instruction=(
            "You are a bank bill payment analyst. The user message contains a customer ID.\n"
            "You MUST call both tools before writing your analysis — do not skip tools or invent numbers.\n"
            "1. Call get_completed_bills with the customer ID to retrieve paid bills from the last month.\n"
            "2. Call get_upcoming_bills with the same customer ID to retrieve scheduled bills for the next month.\n"
            "3. Produce a structured analysis covering:\n"
            "   - Total amount paid last month and number of bills\n"
            "   - Total upcoming obligations and number of bills\n"
            "   - Largest single upcoming payment\n"
            "   - Payment consistency (on-time track record)\n"
            "   - Liability outlook (manageable / stretched / at-risk)\n"
            "Format the output as a clear markdown section titled '## Bill Payment Analysis'."
        ),
        tools=[get_completed_bills, get_upcoming_bills],
        output_key="bill_analysis",
    )

    decision_agent = LlmAgent(
        name="decision_agent",
        model=llm,
        description="Makes the final overdraft approval or denial recommendation.",
        instruction=(
            "You are a senior credit officer at a business bank.\n\n"
            "The user message contains a customer ID. Call get_overdraft_request to get "
            "the customer's account details and requested overdraft limit.\n\n"
            "**Mandatory (demo dataset):** The tool response includes `demo_expected_decision` "
            "(APPROVE, DENY, or CONDITIONAL APPROVE) for this project's fixed mock customers. "
            "Your line **Decision** MUST use that exact outcome. The analyses below should "
            "justify it with real numbers — do not contradict `demo_expected_decision`.\n\n"
            "Then read the previous agents' findings from session state:\n"
            "  - Deposit & balance analysis: {deposit_analysis}\n"
            "  - Bill payment analysis: {bill_analysis}\n\n"
            "Based on ALL this information, produce a final overdraft decision:\n"
            "1. **Decision**: Must match `demo_expected_decision` from the tool (APPROVE, CONDITIONAL APPROVE, or DENY)\n"
            "2. **Recommended Limit**: The overdraft amount you recommend (may differ from requested)\n"
            "3. **Risk Rating**: Low / Medium / High\n"
            "4. **Key Factors**: 3-5 bullet points explaining your reasoning\n"
            "5. **Conditions** (if conditional): What the customer must do\n\n"
            "Format as a markdown section titled '## Overdraft Decision'.\n"
            "Be specific — reference actual numbers from the analyses."
        ),
        tools=[get_overdraft_request],
        output_key="overdraft_decision",
    )

    return SequentialAgent(
        name="banking_overdraft_pipeline",
        description=(
            "Module 07: SequentialAgent pipeline — deposit_agent → bill_agent → decision_agent. "
            "Analyzes a business customer's cash flow and bills, then recommends overdraft approval."
        ),
        sub_agents=[deposit_agent, bill_agent, decision_agent],
    )
