"""Load and index OpenAPI specifications for Module 11."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

HTTP_METHODS = ("get", "post", "put", "patch", "delete", "options", "head")


@dataclass(frozen=True)
class SpecSummary:
    name: str
    title: str
    version: str
    source_file: str
    operation_count: int
    tags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OperationRecord:
    operation_id: str
    spec_name: str
    source_file: str
    spec_title: str
    spec_version: str
    method: str
    path: str
    summary: str
    description: str
    tags: tuple[str, ...]
    parameters: tuple[dict[str, Any], ...]
    request_body: dict[str, Any] | None
    responses: dict[str, Any]
    operation: dict[str, Any]

    def haystack(self) -> str:
        parts = [
            self.operation_id,
            self.spec_name,
            self.spec_title,
            self.method,
            self.path,
            self.summary,
            self.description,
            " ".join(self.tags),
        ]
        return " ".join(part for part in parts if part).lower()

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "operationId": self.operation_id,
            "specName": self.spec_name,
            "specTitle": self.spec_title,
            "method": self.method,
            "path": self.path,
            "summary": self.summary,
            "tags": list(self.tags),
            "sourceFile": self.source_file,
        }

    def to_detail_dict(self) -> dict[str, Any]:
        return {
            "operationId": self.operation_id,
            "specName": self.spec_name,
            "specTitle": self.spec_title,
            "specVersion": self.spec_version,
            "sourceFile": self.source_file,
            "method": self.method,
            "path": self.path,
            "summary": self.summary,
            "description": self.description,
            "tags": list(self.tags),
            "parameters": list(self.parameters),
            "requestBody": self.request_body,
            "responses": self.responses,
            "operation": copy.deepcopy(self.operation),
        }


class OpenApiIndex:
    def __init__(
        self,
        specs_dir: Path,
        specs: list[SpecSummary],
        operations: dict[str, OperationRecord],
    ) -> None:
        self.specs_dir = specs_dir
        self._specs = tuple(specs)
        self._operations = dict(operations)

    @property
    def spec_count(self) -> int:
        return len(self._specs)

    @property
    def operation_count(self) -> int:
        return len(self._operations)

    def list_specs(self) -> list[dict[str, Any]]:
        return [summary.to_dict() for summary in self._specs]

    def list_tags(self) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for operation in self._operations.values():
            for tag in operation.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return [
            {"tag": tag, "operationCount": counts[tag]}
            for tag in sorted(counts)
        ]

    def get_operation(self, operation_id: str) -> dict[str, Any] | None:
        record = self._operations.get(operation_id)
        if record is None:
            return None
        return record.to_detail_dict()

    def get_operation_record(self, operation_id: str) -> OperationRecord | None:
        return self._operations.get(operation_id)

    def summarize_surface(self, spec_name: str | None = None) -> dict[str, Any]:
        records = [
            record
            for record in self._operations.values()
            if not spec_name or record.spec_name == spec_name
        ]
        tag_counts: dict[str, int] = {}
        for record in records:
            for tag in record.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return {
            "specsDir": str(self.specs_dir),
            "specCount": self.spec_count,
            "operationCount": len(records),
            "tagCounts": tag_counts,
            "sampleOperations": [record.to_summary_dict() for record in records[:10]],
        }

    def search_operations(
        self,
        query: str = "",
        method: str | None = None,
        tag: str | None = None,
        spec_name: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        query_tokens = [token for token in _tokenize(query) if token]
        normalized_method = method.lower() if method else None
        normalized_tag = tag.lower() if tag else None
        normalized_spec = spec_name.lower() if spec_name else None

        scored: list[tuple[int, OperationRecord]] = []
        for record in self._operations.values():
            if normalized_method and record.method.lower() != normalized_method:
                continue
            if normalized_tag and normalized_tag not in {item.lower() for item in record.tags}:
                continue
            if normalized_spec and record.spec_name.lower() != normalized_spec:
                continue

            haystack = record.haystack()
            score = 0
            if query_tokens:
                for token in query_tokens:
                    if token in haystack:
                        score += 1
                if score == 0:
                    continue
                if record.operation_id.lower() == query.strip().lower():
                    score += 6
                if query.strip().lower() in record.path.lower():
                    score += 3
            else:
                score = 1

            scored.append((score, record))

        scored.sort(
            key=lambda item: (
                -item[0],
                item[1].spec_name.lower(),
                item[1].path.lower(),
                item[1].method.lower(),
            )
        )
        return [record.to_summary_dict() for _, record in scored[: max(1, limit)]]


def load_openapi_index(specs_dir: str | Path) -> OpenApiIndex:
    resolved_specs_dir = Path(specs_dir).expanduser().resolve()
    if not resolved_specs_dir.exists():
        raise FileNotFoundError(f"OpenAPI specs directory does not exist: {resolved_specs_dir}")

    spec_paths = sorted(
        path
        for pattern in ("*.json", "*.yaml", "*.yml")
        for path in resolved_specs_dir.rglob(pattern)
        if path.is_file()
    )

    specs: list[SpecSummary] = []
    operations: dict[str, OperationRecord] = {}
    operation_counts: dict[Path, int] = {}

    for spec_path in spec_paths:
        document = _load_document(spec_path)
        if not isinstance(document, dict):
            continue

        paths = document.get("paths")
        if not isinstance(paths, dict):
            continue

        info = document.get("info") or {}
        spec_name = spec_path.stem
        spec_title = str(info.get("title") or spec_name)
        spec_version = str(info.get("version") or "")
        spec_tags: set[str] = set()
        operation_counts[spec_path] = 0

        for route_path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                    continue

                record = _build_operation_record(
                    document=document,
                    spec_path=spec_path,
                    spec_name=spec_name,
                    spec_title=spec_title,
                    spec_version=spec_version,
                    route_path=str(route_path),
                    method=method.lower(),
                    path_item=path_item,
                    operation=operation,
                    existing_ids=set(operations),
                )
                operations[record.operation_id] = record
                operation_counts[spec_path] += 1
                spec_tags.update(record.tags)

        specs.append(
            SpecSummary(
                name=spec_name,
                title=spec_title,
                version=spec_version,
                source_file=str(spec_path),
                operation_count=operation_counts[spec_path],
                tags=tuple(sorted(spec_tags)),
            )
        )

    return OpenApiIndex(
        specs_dir=resolved_specs_dir,
        specs=specs,
        operations=operations,
    )


def _build_operation_record(
    *,
    document: dict[str, Any],
    spec_path: Path,
    spec_name: str,
    spec_title: str,
    spec_version: str,
    route_path: str,
    method: str,
    path_item: dict[str, Any],
    operation: dict[str, Any],
    existing_ids: set[str],
) -> OperationRecord:
    resolved_operation = _resolve_refs(copy.deepcopy(operation), document)
    operation_id = _unique_operation_id(
        str(resolved_operation.get("operationId") or _synthetic_operation_id(method, route_path)),
        existing_ids,
    )

    parameters = tuple(
        _normalize_parameter(parameter, document)
        for parameter in _merge_parameters(path_item.get("parameters"), operation.get("parameters"))
    )
    request_body = None
    if resolved_operation.get("requestBody"):
        request_body = _normalize_request_body(resolved_operation["requestBody"])

    responses = _normalize_responses(resolved_operation.get("responses") or {})
    tags = tuple(str(tag) for tag in resolved_operation.get("tags") or ())

    normalized_operation = {
        "operationId": operation_id,
        "method": method.upper(),
        "path": route_path,
        "summary": str(resolved_operation.get("summary") or ""),
        "description": str(resolved_operation.get("description") or ""),
        "tags": list(tags),
        "parameters": list(parameters),
        "requestBody": request_body,
        "responses": responses,
    }

    return OperationRecord(
        operation_id=operation_id,
        spec_name=spec_name,
        source_file=str(spec_path),
        spec_title=spec_title,
        spec_version=spec_version,
        method=method.upper(),
        path=route_path,
        summary=normalized_operation["summary"],
        description=normalized_operation["description"],
        tags=tags,
        parameters=parameters,
        request_body=request_body,
        responses=responses,
        operation=normalized_operation,
    )


def _load_document(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def _merge_parameters(
    path_parameters: Any,
    operation_parameters: Any,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for collection in (path_parameters or [], operation_parameters or []):
        if not isinstance(collection, list):
            continue
        for item in collection:
            if not isinstance(item, dict):
                continue
            key = (str(item.get("name") or ""), str(item.get("in") or ""))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _normalize_parameter(parameter: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    resolved = _resolve_refs(copy.deepcopy(parameter), document)
    return {
        "name": str(resolved.get("name") or ""),
        "in": str(resolved.get("in") or "query"),
        "required": bool(resolved.get("required", False)),
        "description": str(resolved.get("description") or ""),
        "schema": resolved.get("schema") or {},
    }


def _normalize_request_body(request_body: dict[str, Any]) -> dict[str, Any]:
    content = request_body.get("content") or {}
    normalized_content: dict[str, Any] = {}
    for media_type, media_config in content.items():
        if not isinstance(media_config, dict):
            continue
        normalized_content[str(media_type)] = {
            "schema": media_config.get("schema") or {},
            "example": media_config.get("example"),
            "examples": media_config.get("examples") or {},
        }
    return {
        "required": bool(request_body.get("required", False)),
        "description": str(request_body.get("description") or ""),
        "content": normalized_content,
    }


def _normalize_responses(responses: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for status_code, response in responses.items():
        if not isinstance(response, dict):
            continue
        content = response.get("content") or {}
        headers = response.get("headers") or {}
        normalized_content: dict[str, Any] = {}
        normalized_headers: dict[str, Any] = {}
        for media_type, media_config in content.items():
            if not isinstance(media_config, dict):
                continue
            normalized_content[str(media_type)] = {
                "schema": media_config.get("schema") or {},
                "example": media_config.get("example"),
                "examples": media_config.get("examples") or {},
            }
        for header_name, header_config in headers.items():
            if not isinstance(header_config, dict):
                continue
            normalized_headers[str(header_name)] = {
                "description": str(header_config.get("description") or ""),
                "schema": header_config.get("schema") or {},
            }

        normalized[str(status_code)] = {
            "description": str(response.get("description") or ""),
            "headers": normalized_headers,
            "content": normalized_content,
        }
    return normalized


def _resolve_refs(node: Any, document: dict[str, Any], trail: tuple[str, ...] = ()) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            if not isinstance(ref, str) or not ref.startswith("#/"):
                return node
            if ref in trail:
                return {"$ref": ref, "circularRef": True}
            resolved_target = _resolve_pointer(document, ref)
            resolved_value = _resolve_refs(copy.deepcopy(resolved_target), document, trail + (ref,))
            extras = {
                key: _resolve_refs(value, document, trail)
                for key, value in node.items()
                if key != "$ref"
            }
            if isinstance(resolved_value, dict):
                resolved_value.update(extras)
            return resolved_value
        return {key: _resolve_refs(value, document, trail) for key, value in node.items()}
    if isinstance(node, list):
        return [_resolve_refs(item, document, trail) for item in node]
    return node


def _resolve_pointer(document: dict[str, Any], ref: str) -> Any:
    current: Any = document
    for token in ref.removeprefix("#/").split("/"):
        resolved_token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict):
            return {"$ref": ref, "unresolved": True}
        current = current.get(resolved_token)
        if current is None:
            return {"$ref": ref, "unresolved": True}
    return current


def _synthetic_operation_id(method: str, route_path: str) -> str:
    raw = f"{method}_{route_path}"
    return re.sub(r"[^a-zA-Z0-9]+", "_", raw).strip("_").lower()


def _unique_operation_id(base_id: str, existing_ids: set[str]) -> str:
    candidate = base_id
    suffix = 2
    while candidate in existing_ids:
        candidate = f"{base_id}_{suffix}"
        suffix += 1
    return candidate


def _tokenize(value: str) -> list[str]:
    return [token for token in re.split(r"[^a-zA-Z0-9_]+", value.lower()) if token]
