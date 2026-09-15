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
