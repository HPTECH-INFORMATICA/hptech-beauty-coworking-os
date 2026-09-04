"""Regression tests for the frozen BCOS M2 OpenAPI contract."""

from __future__ import annotations

from typing import Any

from bcos_api.main import app

EXPECTED_M2_RESPONSES: dict[tuple[str, str], set[str]] = {
    ("get", "/api/v1/units"): {"200", "401", "403"},
    ("post", "/api/v1/units"): {"201", "400", "401", "403", "422"},
    ("get", "/api/v1/units/{unit_id}"): {"200", "404"},
    ("patch", "/api/v1/units/{unit_id}"): {"200", "403", "404", "422"},
    ("get", "/api/v1/units/{unit_id}/reception-hours"): {"200"},
    ("put", "/api/v1/units/{unit_id}/reception-hours"): {"200", "403", "422"},
    ("get", "/api/v1/professionals"): {"200"},
    ("post", "/api/v1/professionals"): {"201", "403", "409", "422"},
    ("get", "/api/v1/professionals/{professional_id}"): {"200", "404"},
    ("patch", "/api/v1/professionals/{professional_id}"): {"200", "403", "404"},
    ("get", "/api/v1/resource-categories"): {"200"},
    ("post", "/api/v1/resource-categories"): {"201", "403", "409"},
    ("get", "/api/v1/resources"): {"200"},
    ("post", "/api/v1/resources"): {"201", "403", "409", "422"},
    ("get", "/api/v1/resources/{resource_id}"): {"200", "404"},
    ("patch", "/api/v1/resources/{resource_id}"): {"200", "403", "404"},
}


def _schema() -> dict[str, Any]:
    return app.openapi()


def test_m2_response_map_matches_frozen_contract() -> None:
    schema = _schema()

    for (method, path), expected in EXPECTED_M2_RESPONSES.items():
        actual = set(schema["paths"][path][method]["responses"])
        assert actual == expected, (
            f"{method.upper()} {path}: "
            f"expected {sorted(expected)}, got {sorted(actual)}"
        )


def test_error_response_matches_frozen_core_shape() -> None:
    schema = _schema()
    error_schema = schema["components"]["schemas"]["ErrorResponse"]

    assert error_schema["additionalProperties"] is False
    assert set(error_schema["required"]) == {"code", "message"}

    properties = error_schema["properties"]

    assert properties["code"]["type"] == "string"
    assert properties["message"]["type"] == "string"

    request_id_variants = properties["request_id"]["anyOf"]
    assert {"type": "string"} in request_id_variants
    assert {"type": "null"} in request_id_variants

    details_variants = properties["details"]["anyOf"]
    assert {"type": "null"} in details_variants
    assert {
        "additionalProperties": True,
        "type": "object",
    } in details_variants


def test_declared_m2_errors_reference_error_response() -> None:
    schema = _schema()

    for (method, path), response_codes in EXPECTED_M2_RESPONSES.items():
        operation = schema["paths"][path][method]

        for response_code in response_codes:
            if response_code.startswith("2"):
                continue

            response = operation["responses"][response_code]
            content = response["content"]["application/json"]
            response_schema = content["schema"]

            assert response_schema == {
                "$ref": "#/components/schemas/ErrorResponse"
            }, f"{method.upper()} {path} {response_code}"
