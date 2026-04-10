"""Generate example payloads from normalized OpenAPI schemas."""

from __future__ import annotations

from typing import Any

MAX_SCHEMA_DEPTH = 6
DEFAULT_UUID = "123e4567-e89b-12d3-a456-426614174000"


def generate_schema_example(schema: dict[str, Any] | None, depth: int = 0) -> Any:
    """Return a deterministic example value for a resolved JSON schema."""
    if not schema:
        return {}
    if depth > MAX_SCHEMA_DEPTH:
        return None

    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if "const" in schema:
        return schema["const"]
    if schema.get("enum"):
        return schema["enum"][0]

    examples = schema.get("examples")
    if isinstance(examples, list) and examples:
        return examples[0]
    if isinstance(examples, dict) and examples:
        first = next(iter(examples.values()))
        if isinstance(first, dict) and "value" in first:
            return first["value"]
        return first

    if schema.get("oneOf"):
        return generate_schema_example(schema["oneOf"][0], depth + 1)
    if schema.get("anyOf"):
        return generate_schema_example(schema["anyOf"][0], depth + 1)
    if schema.get("allOf"):
        merged: dict[str, Any] = {}
        for item in schema["allOf"]:
            candidate = generate_schema_example(item, depth + 1)
            if isinstance(candidate, dict):
                merged.update(candidate)
        if merged:
            return merged
        return generate_schema_example(schema["allOf"][0], depth + 1)

    schema_type = schema.get("type")
    if not schema_type:
        if "properties" in schema or "additionalProperties" in schema:
            schema_type = "object"
        elif "items" in schema:
            schema_type = "array"

    if schema_type == "object":
        result: dict[str, Any] = {}
        properties = schema.get("properties", {})
        for key, child_schema in properties.items():
            result[key] = generate_schema_example(child_schema, depth + 1)

        additional = schema.get("additionalProperties")
        if isinstance(additional, dict) and "additionalProp1" not in result:
            result["additionalProp1"] = generate_schema_example(additional, depth + 1)
        return result

    if schema_type == "array":
        return [generate_schema_example(schema.get("items", {}), depth + 1)]

    if schema_type == "integer":
        if "minimum" in schema:
            return int(schema["minimum"])
        return 1

    if schema_type == "number":
        if "minimum" in schema:
            return float(schema["minimum"])
        return 1.0

    if schema_type == "boolean":
        return True

    if schema_type == "string":
        fmt = schema.get("format")
        if fmt == "date-time":
            return "2026-04-09T12:00:00Z"
        if fmt == "date":
            return "2026-04-09"
        if fmt == "time":
            return "12:00:00Z"
        if fmt == "uuid":
            return DEFAULT_UUID
        if fmt == "email":
            return "user@example.com"
        if fmt in {"uri", "url"}:
            return "https://api.example.com/resource"
        if fmt == "binary":
            return "<binary>"
        if fmt == "byte":
            return "Ynl0ZXM="
        if fmt == "ipv4":
            return "127.0.0.1"
        if fmt == "ipv6":
            return "::1"
        if fmt == "hostname":
            return "api.example.com"
        if fmt == "password":
            return "secret-password"
        if schema.get("pattern"):
            return "string-matching-pattern"
        if schema.get("minLength", 0) > 8:
            return "sample-text"
        return "string"

    return "value"


def build_mock_request(operation: dict[str, Any]) -> dict[str, Any]:
    """Generate example inputs for an operation's parameters and request body."""
    grouped_params: dict[str, dict[str, Any]] = {
        "path": {},
        "query": {},
        "header": {},
        "cookie": {},
    }
    for parameter in operation.get("parameters", []):
        location = parameter.get("in") or "query"
        if location not in grouped_params:
            continue
        grouped_params[location][parameter["name"]] = generate_schema_example(parameter.get("schema"))

    request_body = operation.get("requestBody") or {}
    content = request_body.get("content") or {}
    media_type = next(iter(content.keys()), None)
    body_example = None
    if media_type:
        body_example = generate_schema_example(content[media_type].get("schema"))

    return {
        "operationId": operation.get("operationId"),
        "method": operation.get("method"),
        "path": operation.get("path"),
        "pathParams": grouped_params["path"],
        "queryParams": grouped_params["query"],
        "headers": grouped_params["header"],
        "cookies": grouped_params["cookie"],
        "contentType": media_type,
        "body": body_example,
    }


def build_mock_response(operation: dict[str, Any], status_code: str | None = None) -> dict[str, Any]:
    """Generate an example response payload for the chosen status code."""
    responses = operation.get("responses") or {}
    resolved_status = status_code or _choose_default_status_code(responses)
    response = responses.get(resolved_status, {})

    content = response.get("content") or {}
    media_type = next(iter(content.keys()), None)
    body_example = None
    if media_type:
        body_example = generate_schema_example(content[media_type].get("schema"))

    headers: dict[str, Any] = {}
    for header_name, header_schema in (response.get("headers") or {}).items():
        headers[header_name] = generate_schema_example(header_schema.get("schema"))

    return {
        "operationId": operation.get("operationId"),
        "method": operation.get("method"),
        "path": operation.get("path"),
        "statusCode": resolved_status,
        "contentType": media_type,
        "headers": headers,
        "body": body_example,
    }


def _choose_default_status_code(responses: dict[str, Any]) -> str:
    if not responses:
        return "default"

    for code in responses:
        if str(code).startswith("2"):
            return str(code)
    if "default" in responses:
        return "default"
    return str(next(iter(responses)))
