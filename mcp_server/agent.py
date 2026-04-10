"""Module 11 ADK agent wired to the local or remote MCP server."""

from __future__ import annotations

import json
import os
import shlex
import sys
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from mcp import StdioServerParameters

from simple_litellm_agent.config import Settings, get_settings

MIN_MCP_TOKENS = 896
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_TRANSPORT = "stdio"
DEFAULT_HTTP_URL = "http://127.0.0.1:8765/mcp"
DEFAULT_HTTP_READ_TIMEOUT_SECONDS = 300.0


def _build_llm(settings: Settings) -> LiteLlm:
    return LiteLlm(
        model=settings.litellm_model,
        api_base=settings.api_base,
        api_key=settings.api_key,
        max_tokens=max(settings.max_tokens, MIN_MCP_TOKENS),
    )


def _transport() -> str:
    raw = os.getenv("MODULE11_MCP_TRANSPORT", DEFAULT_TRANSPORT).strip().lower()
    return raw or DEFAULT_TRANSPORT


def _timeout() -> float:
    raw = os.getenv("MODULE11_MCP_TIMEOUT", "").strip()
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        parsed = float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return parsed if parsed > 0 else DEFAULT_TIMEOUT_SECONDS


def _http_read_timeout() -> float:
    raw = os.getenv("MODULE11_MCP_HTTP_READ_TIMEOUT", "").strip()
    if not raw:
        return DEFAULT_HTTP_READ_TIMEOUT_SECONDS
    try:
        parsed = float(raw)
    except ValueError:
        return DEFAULT_HTTP_READ_TIMEOUT_SECONDS
    return parsed if parsed > 0 else DEFAULT_HTTP_READ_TIMEOUT_SECONDS


def _stdio_command() -> str:
    raw = os.getenv("MODULE11_MCP_COMMAND", "").strip()
    if raw:
        return raw
    return sys.executable


def _stdio_args() -> list[str]:
    raw = os.getenv("MODULE11_MCP_ARGS", "").strip()
    if raw:
        return shlex.split(raw)

    args = ["-m", "mcp_server.server", "--transport", "stdio"]
    specs_dir = os.getenv("MODULE11_SPECS_DIR", "").strip()
    if specs_dir:
        args.extend(["--specs-dir", specs_dir])
    return args


def _http_headers() -> dict[str, Any] | None:
    raw = os.getenv("MODULE11_MCP_HTTP_HEADERS_JSON", "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _http_url() -> str:
    raw = os.getenv("MODULE11_MCP_HTTP_URL", "").strip()
    if raw:
        return raw
    return DEFAULT_HTTP_URL


def _build_toolset() -> McpToolset:
    transport = _transport()
    if transport == "streamable-http":
        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=_http_url(),
                headers=_http_headers(),
                timeout=_timeout(),
                sse_read_timeout=_http_read_timeout(),
            ),
        )

    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=_stdio_command(),
                args=_stdio_args(),
            ),
            timeout=_timeout(),
        ),
    )


def create_agent(settings: Settings | None = None) -> LlmAgent:
    resolved = settings or get_settings()
    return LlmAgent(
        name="module11_openapi_mcp_agent",
        model=_build_llm(resolved),
        description="Module 11 MCP client agent for OpenAPI search, schema lookup, and mock generation.",
        instruction=(
            "You are an API integration assistant backed by an OpenAPI-aware MCP server.\n"
            "Always use MCP tools before answering API questions.\n"
            "Preferred workflow:\n"
            "1. Use search_operations or summarize_api_surface when the user describes a capability.\n"
            "2. Use get_operation_details when the user asks for schemas, operation metadata, or the full spec shape.\n"
            "3. Use generate_mock_request or generate_mock_response when the user asks for examples or payload mocks.\n"
            "4. Mention the operationId and HTTP method/path in your final answer.\n"
            "If no specs are loaded, explain that Module 11 reads OpenAPI files from MODULE11_SPECS_DIR at server startup.\n"
            "Keep replies concise and implementation-focused."
        ),
        tools=[_build_toolset()],
    )
