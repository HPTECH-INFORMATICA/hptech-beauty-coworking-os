from bcos_api.main import create_app


def test_frozen_reception_routes_are_exposed() -> None:
    schema = create_app().openapi()

    now_operation = schema["paths"]["/api/v1/reception/now"]["get"]
    agenda_operation = schema["paths"]["/api/v1/reception/agenda"]["get"]

    assert now_operation["operationId"] == "getReceptionNow"
    assert agenda_operation["operationId"] == "getReceptionAgenda"


def test_reception_agenda_preserves_booking_usage_boundary() -> None:
    schema = create_app().openapi()
    agenda_schema = schema["components"]["schemas"]["AgendaEntry"]

    assert set(agenda_schema["required"]) == {"booking"}
    assert "usage" in agenda_schema["properties"]
