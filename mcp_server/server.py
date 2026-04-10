"""Module 11 MCP server exposing OpenAPI discovery tools."""

from __future__ import annotations

import argparse
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .mock_payloads import build_mock_request, build_mock_response
from .openapi_loader import OpenApiIndex, load_openapi_index

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_HTTP_PATH = "/mcp"
DEFAULT_TRANSPORT = "stdio"


def default_specs_dir() -> Path:
    return Path(__file__).resolve().parent / "specs"


def configured_specs_dir() -> Path:
    raw = os.getenv("MODULE11_SPECS_DIR", "").strip()
    if raw:
        return Path(raw).expanduser()
    return default_specs_dir()


def configured_transport() -> str:
    raw = os.getenv("MODULE11_SERVER_TRANSPORT", DEFAULT_TRANSPORT).strip().lower()
    return raw or DEFAULT_TRANSPORT


def configured_host() -> str:
    raw = os.getenv("MODULE11_MCP_HOST", DEFAULT_HOST).strip()
    return raw or DEFAULT_HOST


def configured_port() -> int:
    raw = os.getenv("MODULE11_MCP_PORT", "").strip()
    if not raw:
        return DEFAULT_PORT
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_PORT
    return parsed if parsed > 0 else DEFAULT_PORT


def configured_http_path() -> str:
    raw = os.getenv("MODULE11_MCP_HTTP_PATH", DEFAULT_HTTP_PATH).strip()
    if not raw:
        return DEFAULT_HTTP_PATH
    return raw if raw.startswith("/") else f"/{raw}"


@lru_cache(maxsize=1)
def get_openapi_index() -> OpenApiIndex:
    return load_openapi_index(configured_specs_dir())


def reset_openapi_index() -> None:
    get_openapi_index.cache_clear()


def create_server(
    *,
    specs_dir: str | Path | None = None,
    host: str | None = None,
    port: int | None = None,
    streamable_http_path: str | None = None,
) -> FastMCP:
    resolved_specs_dir = Path(specs_dir).expanduser() if specs_dir else configured_specs_dir()
    index = load_openapi_index(resolved_specs_dir)

    server = FastMCP(
        "Module11OpenApiServer",
        instructions=(
            "OpenAPI artifact MCP server for Module 11. Search operations, inspect "
            "resolved request/response schemas, and generate mock payloads from specs."
        ),
        host=host or configured_host(),
        port=port or configured_port(),
        streamable_http_path=streamable_http_path or configured_http_path(),
        json_response=True,
        stateless_http=True,
    )

    @server.tool(
        name="list_specs",
        description="List loaded OpenAPI specification files and operation counts.",
    )
    def list_specs() -> dict[str, Any]:
        return {
            "specsDir": str(index.specs_dir),
            "specCount": index.spec_count,
            "operationCount": index.operation_count,
            "specs": index.list_specs(),
        }

    @server.tool(
        name="list_tags",
        description="List tags discovered across all loaded OpenAPI operations.",
    )
    def list_tags() -> dict[str, Any]:
        return {
            "specsDir": str(index.specs_dir),
            "tags": index.list_tags(),
        }

    @server.tool(
        name="summarize_api_surface",
        description="Summarize the available API surface for a spec or the full index.",
    )
    def summarize_api_surface(spec_name: str | None = None) -> dict[str, Any]:
        return index.summarize_surface(spec_name=spec_name)

    @server.tool(
        name="search_operations",
        description="Search operations by operationId, path, method, tags, or description keywords.",
    )
    def search_operations(
        query: str = "",
        method: str | None = None,
        tag: str | None = None,
        spec_name: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        return {
            "query": query,
            "results": index.search_operations(
                query=query,
                method=method,
                tag=tag,
                spec_name=spec_name,
                limit=max(1, min(limit, 25)),
            ),
        }

    @server.tool(
        name="get_operation_details",
        description="Return a fully resolved operation record by operationId.",
    )
    def get_operation_details(operation_id: str) -> dict[str, Any]:
        operation = index.get_operation(operation_id)
        if operation is None:
            return {
                "error": f"Unknown operationId: {operation_id}",
                "availableOperationIds": [
                    item["operationId"]
                    for item in index.search_operations(query=operation_id, limit=5)
                ],
            }
        return operation

    @server.tool(
        name="generate_mock_request",
        description="Generate a mock request payload for an operationId.",
    )
    def generate_mock_request(operation_id: str) -> dict[str, Any]:
        operation = index.get_operation(operation_id)
        if operation is None:
            return {"error": f"Unknown operationId: {operation_id}"}
        return build_mock_request(operation)

    @server.tool(
        name="generate_mock_response",
        description="Generate a mock response payload for an operationId and optional status code.",
    )
    def generate_mock_response(operation_id: str, status_code: str | None = None) -> dict[str, Any]:
        operation = index.get_operation(operation_id)
        if operation is None:
            return {"error": f"Unknown operationId: {operation_id}"}
        return build_mock_response(operation, status_code=status_code)

    return server


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Module 11 OpenAPI-backed MCP server.",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default=configured_transport(),
        help="Use stdio for local spawned MCP sessions or streamable-http for a remote server.",
    )
    parser.add_argument(
        "--specs-dir",
        default=str(configured_specs_dir()),
        help="Directory containing .json/.yaml/.yml OpenAPI specs.",
    )
    parser.add_argument(
        "--host",
        default=configured_host(),
        help="Host to bind when transport=streamable-http.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=configured_port(),
        help="Port to bind when transport=streamable-http.",
    )
    parser.add_argument(
        "--http-path",
        default=configured_http_path(),
        help="Streamable HTTP path when transport=streamable-http.",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print the resolved startup config before launching the server.",
    )
    args = parser.parse_args()

    if args.print_config:
        print(
            json.dumps(
                {
                    "transport": args.transport,
                    "specsDir": args.specs_dir,
                    "host": args.host,
                    "port": args.port,
                    "httpPath": args.http_path,
                },
                indent=2,
            )
        )

    server = create_server(
        specs_dir=args.specs_dir,
        host=args.host,
        port=args.port,
        streamable_http_path=args.http_path,
    )
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
