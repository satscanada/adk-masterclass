"""Module 10 MCP client agent builders."""

from __future__ import annotations

import os
import shlex
from urllib.parse import quote

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from simple_litellm_agent.config import Settings, get_settings

MIN_MCP_TOKENS = 896
DEFAULT_MCP_COMMAND = "uvx"
DEFAULT_MCP_ARGS = "--from redis-mcp-server@latest redis-mcp-server"
DEFAULT_MCP_TIMEOUT_SECONDS = 20.0
DEFAULT_REDIS_HOST = "127.0.0.1"
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0


def _build_llm(settings: Settings) -> LiteLlm:
    return LiteLlm(
        model=settings.litellm_model,
        api_base=settings.api_base,
        api_key=settings.api_key,
        max_tokens=max(settings.max_tokens, MIN_MCP_TOKENS),
    )


def _mcp_command() -> str:
    raw = os.getenv("MODULE10_MCP_COMMAND", DEFAULT_MCP_COMMAND).strip()
    return raw or DEFAULT_MCP_COMMAND


def _mcp_args() -> list[str]:
    raw = os.getenv("MODULE10_MCP_ARGS", DEFAULT_MCP_ARGS).strip()
    if not raw:
        base_args = shlex.split(DEFAULT_MCP_ARGS)
    else:
        base_args = shlex.split(raw)

    # Official redis-mcp-server supports --url or individual --host/--port/--db args.
    has_explicit_connection = any(
        token in base_args for token in ("--url", "--host", "--port", "--db")
    ) or any(arg.startswith("redis://") or arg.startswith("rediss://") for arg in base_args)
    if has_explicit_connection:
        return base_args
    return [*base_args, "--url", _redis_url()]


def _mcp_timeout() -> float:
    raw = os.getenv("MODULE10_MCP_TIMEOUT", "").strip()
    if not raw:
        return DEFAULT_MCP_TIMEOUT_SECONDS
    try:
        parsed = float(raw)
    except ValueError:
        return DEFAULT_MCP_TIMEOUT_SECONDS
    return parsed if parsed > 0 else DEFAULT_MCP_TIMEOUT_SECONDS


def _redis_port() -> int:
    raw = os.getenv("MODULE10_REDIS_PORT", "").strip()
    if not raw:
        return DEFAULT_REDIS_PORT
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_REDIS_PORT
    return parsed if parsed > 0 else DEFAULT_REDIS_PORT


def _redis_db() -> int:
    raw = os.getenv("MODULE10_REDIS_DB", "").strip()
    if not raw:
        return DEFAULT_REDIS_DB
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_REDIS_DB
    return parsed if parsed >= 0 else DEFAULT_REDIS_DB


def _redis_url() -> str:
    explicit = os.getenv("MODULE10_REDIS_URL", "").strip()
    if explicit:
        return explicit

    host = os.getenv("MODULE10_REDIS_HOST", DEFAULT_REDIS_HOST).strip() or DEFAULT_REDIS_HOST
    username = os.getenv("MODULE10_REDIS_USERNAME", "").strip()
    password = os.getenv("MODULE10_REDIS_PASSWORD", "").strip()

    auth = ""
    if username and password:
        auth = f"{quote(username, safe='')}:{quote(password, safe='')}@"
    elif password:
        auth = f":{quote(password, safe='')}@"
    elif username:
        auth = f"{quote(username, safe='')}@"

    return f"redis://{auth}{host}:{_redis_port()}/{_redis_db()}"


def _build_redis_toolset() -> McpToolset:
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=_mcp_command(),
                args=_mcp_args(),
            ),
            timeout=_mcp_timeout(),
        ),
    )


def create_agent(settings: Settings | None = None) -> LlmAgent:
    resolved = settings or get_settings()
    return LlmAgent(
        name="module10_mcp_redis_banking_agent",
        model=_build_llm(resolved),
        description="Module 10 MCP client agent using a Redis MCP server for business banking memory.",
        instruction=(
            "You are a business banking relationship assistant for overdraft and cash-flow coaching.\n"
            "Always use Redis MCP tools to persist and retrieve customer working memory.\n"
            "Key strategy (infer the customer id from the user message, e.g. CUST-1001):\n"
            "- Key prefix: banking:customer:<that id>:\n"
            "- Summary key: banking:customer:<that id>:summary\n"
            "- Next-action key: banking:customer:<that id>:next_action\n"
            "- Before answering, try to fetch existing keys for continuity.\n"
            "When the user names a customer id like CUST-1001 or CUST-2002, produce concise markdown:\n"
            "1) Current situation, 2) Recommended action, 3) Data persisted in Redis.\n"
            "If MCP tools are unavailable, say Redis MCP setup is needed and provide quick setup guidance.\n"
            "Do not use curly braces in Redis key examples in your reasoning; use the actual id from the user."
        ),
        tools=[_build_redis_toolset()],
    )
