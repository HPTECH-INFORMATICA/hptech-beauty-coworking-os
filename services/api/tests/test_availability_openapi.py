"""Regression tests for the frozen BCOS M3 Availability OpenAPI contract."""

from __future__ import annotations

from typing import Any

from bcos_api.main import app


def _schema() -> dict[str, Any]:
    return app.openapi()


def test_availability_operation_matches_frozen_contract() -> None:
    schema = _schema()
    operation = schema["paths"]["/api/v1/availability"]["get"]

    assert operation["tags"] == ["Availability"]
    assert operation["summary"] == "Consultar disponibilidade"
    assert operation["operationId"] == "getAvailability"
    assert operation["description"] == (
        "Consulta preventiva para UX.\n"
        "Não reserva o recurso; ResourceOccupancy no PostgreSQL "
        "é a autoridade definitiva."
    )

    assert set(operation["responses"]) == {"200", "422"}

    assert operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/AvailabilityResponse"}

    assert operation["responses"]["422"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/ErrorResponse"}


def test_availability_parameters_match_frozen_contract() -> None:
    schema = _schema()
    parameters = schema["paths"]["/api/v1/availability"]["get"]["parameters"]

    assert {parameter["name"] for parameter in parameters} == {
        "X-Tenant-Id",
        "unit_id",
        "starts_at",
        "ends_at",
        "resource_id",
        "category_id",
    }

    by_name = {parameter["name"]: parameter for parameter in parameters}

    assert by_name["X-Tenant-Id"]["in"] == "header"
    assert by_name["X-Tenant-Id"]["required"] is True

    for name in ("unit_id", "starts_at", "ends_at"):
        assert by_name[name]["in"] == "query"
        assert by_name[name]["required"] is True

    for name in ("resource_id", "category_id"):
        assert by_name[name]["in"] == "query"
        assert by_name[name]["required"] is False

    assert by_name["unit_id"]["schema"]["format"] == "uuid"
    assert by_name["starts_at"]["schema"]["format"] == "date-time"
    assert by_name["ends_at"]["schema"]["format"] == "date-time"

    for name in ("resource_id", "category_id"):
        variants = by_name[name]["schema"]["anyOf"]
        assert {"type": "string", "format": "uuid"} in variants
        assert {"type": "null"} in variants


def test_availability_response_schemas_match_frozen_contract() -> None:
    schema = _schema()
    components = schema["components"]["schemas"]

    response_schema = components["AvailabilityResponse"]
    assert set(response_schema["required"]) == {
        "starts_at",
        "ends_at",
        "resources",
    }
    assert set(response_schema["properties"]) == {
        "starts_at",
        "ends_at",
        "resources",
    }
    assert response_schema["properties"]["starts_at"]["format"] == "date-time"
    assert response_schema["properties"]["ends_at"]["format"] == "date-time"
    assert response_schema["properties"]["resources"]["items"] == {
        "$ref": "#/components/schemas/AvailabilityItem"
    }

    item_schema = components["AvailabilityItem"]
    assert set(item_schema["required"]) == {
        "resource_id",
        "available",
    }
    assert set(item_schema["properties"]) == {
        "resource_id",
        "available",
        "reason",
    }
    assert item_schema["properties"]["resource_id"]["format"] == "uuid"
    assert item_schema["properties"]["available"]["type"] == "boolean"

    reason_variants = item_schema["properties"]["reason"]["anyOf"]
    assert {"type": "string"} in reason_variants
    assert {"type": "null"} in reason_variants

