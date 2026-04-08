"""Module 09 agent builders."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import AgentTool, LongRunningFunctionTool

from simple_litellm_agent.config import Settings, get_settings

from .function_tools import (
    apply_exception_clearance,
    ask_for_exception_clearance,
    get_business_overdraft_snapshot,
    get_deposit_recalc_task_status,
    get_retail_deposit_snapshot,
    submit_deposit_recalc_task,
)

MIN_FUNCTION_TOOLS_TOKENS = 768


def _build_llm(settings: Settings) -> LiteLlm:
    return LiteLlm(
        model=settings.litellm_model,
        api_base=settings.api_base,
        api_key=settings.api_key,
        max_tokens=max(settings.max_tokens, MIN_FUNCTION_TOOLS_TOKENS),
    )


def create_basic_tools_agent(settings: Settings | None = None) -> LlmAgent:
    resolved = settings or get_settings()
    llm = _build_llm(resolved)
    return LlmAgent(
        name="module09_basic_tools_agent",
        model=llm,
        description="Module 09 basic function tools using existing banking datasets.",
        instruction=(
            "You are a banking insights assistant. Use tools for facts.\n"
            "- For retail IDs (RET-*), call get_retail_deposit_snapshot.\n"
            "- For business IDs (CUST-*), call get_business_overdraft_snapshot.\n"
            "Return concise markdown with key numbers and one recommendation."
        ),
        tools=[get_retail_deposit_snapshot, get_business_overdraft_snapshot],
    )


def create_long_running_tools_agent(settings: Settings | None = None) -> LlmAgent:
    resolved = settings or get_settings()
    llm = _build_llm(resolved)
    long_tool = LongRunningFunctionTool(ask_for_exception_clearance)
    return LlmAgent(
        name="module09_long_running_agent",
        model=llm,
        description="Module 09 long-running function tool demo.",
        instruction=(
            "You handle deposit exception clearances.\n"
            "When user asks for exception approval, call ask_for_exception_clearance first.\n"
            "After an approval function response is provided, call apply_exception_clearance "
            "with the ticket ID and customer ID, then return a final user-facing status."
        ),
        tools=[long_tool, apply_exception_clearance],
    )


def create_agent_as_tool_root_agent(settings: Settings | None = None) -> LlmAgent:
    resolved = settings or get_settings()
    llm = _build_llm(resolved)

    specialist = LlmAgent(
        name="deposit_specialist_agent",
        model=llm,
        description="Specialist sub-agent for deposit profile interpretation.",
        instruction=(
            "You are a deposit specialist.\n"
            "If request includes RET-* use get_retail_deposit_snapshot.\n"
            "If request includes CUST-* use get_business_overdraft_snapshot.\n"
            "Return concise facts and a short recommendation."
        ),
        tools=[get_retail_deposit_snapshot, get_business_overdraft_snapshot],
    )

    return LlmAgent(
        name="module09_agent_as_tool_root",
        model=llm,
        description="Module 09 agent-as-a-tool demo root agent.",
        instruction=(
            "You are the coordinator. Always delegate analysis requests to the "
            "deposit_specialist_agent tool and present its response directly."
        ),
        tools=[AgentTool(agent=specialist, skip_summarization=True)],
    )


def create_celery_banking_agent(settings: Settings | None = None) -> LlmAgent:
    resolved = settings or get_settings()
    llm = _build_llm(resolved)
    return LlmAgent(
        name="module09_celery_banking_agent",
        model=llm,
        description="Module 09 Celery + Redis async banking tool example.",
        instruction=(
            "You handle asynchronous retail deposit score recalculation.\n"
            "1) Call submit_deposit_recalc_task(customer_id).\n"
            "2) If queued, call get_deposit_recalc_task_status(task_id) once and report state.\n"
            "3) If completed, summarize result fields for the user.\n"
            "If tools return setup/broker error, provide actionable setup guidance."
        ),
        tools=[submit_deposit_recalc_task, get_deposit_recalc_task_status],
    )

