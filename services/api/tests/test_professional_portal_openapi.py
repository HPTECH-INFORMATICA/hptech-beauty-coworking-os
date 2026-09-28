from bcos_api.main import create_app


def test_frozen_professional_portal_routes_are_exposed() -> None:
    schema = create_app().openapi()

    bookings = schema["paths"]["/api/v1/professional/me/bookings"]["get"]
    invoices = schema["paths"]["/api/v1/professional/me/invoices"]["get"]

    assert bookings["operationId"] == "listMyBookings"
    assert invoices["operationId"] == "listMyInvoices"


def test_professional_portal_does_not_accept_client_professional_id() -> None:
    schema = create_app().openapi()

    for path in (
        "/api/v1/professional/me/bookings",
        "/api/v1/professional/me/invoices",
    ):
        parameters = schema["paths"][path]["get"].get("parameters", [])
        names = {parameter.get("name") for parameter in parameters}
        assert "professional_id" not in names


def test_professional_commercial_c3_routes_are_exposed() -> None:
    schema = create_app().openapi()

    commercial = schema["paths"]["/api/v1/professional/me/commercial-availability"]["get"]
    create_booking = schema["paths"]["/api/v1/professional/me/bookings"]["post"]

    assert commercial["operationId"] == "getMyCommercialAvailability"
    assert create_booking["operationId"] == "createMyBooking"
    assert commercial["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ProfessionalCommercialAvailability"
    )


def test_professional_commercial_contract_exposes_server_price_fields() -> None:
    schema = create_app().openapi()
    option = schema["components"]["schemas"]["ProfessionalCommercialOption"]
    properties = option["properties"]

    assert {"price_amount", "price_currency", "price_modality"} <= properties.keys()


def test_professional_booking_create_does_not_accept_professional_id() -> None:
    schema = create_app().openapi()
    payload = schema["components"]["schemas"]["ProfessionalBookingCreate"]
    properties = payload["properties"]

    assert "professional_id" not in properties
