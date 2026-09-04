"""OpenAPI normalization against the frozen BCOS V1 contract."""

from __future__ import annotations

from typing import Any

_M2_OPERATIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("get", "/api/v1/units"),
        ("post", "/api/v1/units"),
        ("get", "/api/v1/units/{unit_id}"),
        ("patch", "/api/v1/units/{unit_id}"),
        ("get", "/api/v1/units/{unit_id}/reception-hours"),
        ("put", "/api/v1/units/{unit_id}/reception-hours"),
        ("get", "/api/v1/professionals"),
        ("post", "/api/v1/professionals"),
        ("get", "/api/v1/professionals/{professional_id}"),
        ("patch", "/api/v1/professionals/{professional_id}"),
        ("get", "/api/v1/resource-categories"),
        ("post", "/api/v1/resource-categories"),
        ("get", "/api/v1/resources"),
        ("post", "/api/v1/resources"),
        ("get", "/api/v1/resources/{resource_id}"),
        ("patch", "/api/v1/resources/{resource_id}"),
    }
)

_M2_422_OPERATIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("post", "/api/v1/units"),
        ("patch", "/api/v1/units/{unit_id}"),
        ("put", "/api/v1/units/{unit_id}/reception-hours"),
        ("post", "/api/v1/professionals"),
        ("post", "/api/v1/resources"),
    }
)


def normalize_openapi_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove only FastAPI-generated M2 422 responses absent from the frozen contract."""

    paths = schema.get("paths")
    if not isinstance(paths, dict):
        return schema

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue

            operation_key = (method, path)

            if operation_key not in _M2_OPERATIONS:
                continue

            if operation_key in _M2_422_OPERATIONS:
                continue

            responses = operation.get("responses")
            if isinstance(responses, dict):
                responses.pop("422", None)

    return schema
