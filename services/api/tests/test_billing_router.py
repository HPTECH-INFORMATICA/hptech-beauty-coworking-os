from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from bcos_api.billing.schemas import InvoiceDetail, InvoiceStatus, InvoiceSummary
from bcos_api.db.session import get_async_session
from bcos_api.main import create_app
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.tenancy.membership import MembershipRole


class FakeSession:
    pass


def make_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(), membership_id=uuid4(),
        external_user_id="identity:test", role=MembershipRole.OWNER,
    )


def summary() -> InvoiceSummary:
    now = datetime(2026, 9, 14, 15, 0, tzinfo=UTC)
    return InvoiceSummary(
        id=uuid4(), professional_id=uuid4(), source_usage_id=uuid4(),
        professional_billing_contract_id=None, billing_cycle_start=None,
        billing_cycle_end=None, manual_closed_at=None, status=InvoiceStatus.OPEN,
        currency="BRL", subtotal_amount=Decimal("80.00"),
        discount_amount=Decimal("0.00"), total_amount=Decimal("80.00"),
        created_at=now, updated_at=now,
    )


def app_with_overrides():
    app = create_app()
    ctx = make_context()
    session = FakeSession()

    async def fake_session():
        yield session

    async def fake_context():
        return ctx

    app.dependency_overrides[get_async_session] = fake_session
    app.dependency_overrides[get_tenant_context] = fake_context
    return app, ctx, session


def test_list_route_maps_pagination_without_writes(monkeypatch) -> None:
    app, ctx, session = app_with_overrides()
    item = summary()
    captured = {}

    async def fake_list(received_session, **kwargs):
        captured.update(kwargs)
        assert received_session is session
        return [item]

    monkeypatch.setattr("bcos_api.billing.router.list_tenant_invoices", fake_list)
    response = TestClient(app).get("/api/v1/invoices?status=OPEN&limit=10&offset=20")
    assert response.status_code == 200
    assert response.json()[0]["id"] == str(item.id)
    assert captured["context"] is ctx
    assert captured["status"] is InvoiceStatus.OPEN
    assert captured["limit"] == 10
    assert captured["offset"] == 20


def test_detail_route_serializes_financial_projection(monkeypatch) -> None:
    app, ctx, session = app_with_overrides()
    item = summary()
    detail = InvoiceDetail(
        **item.model_dump(), items=[], confirmed_amount=Decimal("30.00"),
        remaining_amount=Decimal("50.00"),
    )

    async def fake_get(received_session, **kwargs):
        assert received_session is session
        assert kwargs["context"] is ctx
        return detail

    monkeypatch.setattr("bcos_api.billing.router.get_tenant_invoice", fake_get)
    response = TestClient(app).get(f"/api/v1/invoices/{item.id}")
    assert response.status_code == 200
    assert response.json()["confirmed_amount"] == "30.00"
    assert response.json()["remaining_amount"] == "50.00"


def test_openapi_contains_only_read_billing_routes() -> None:
    schema = create_app().openapi()
    assert "get" in schema["paths"]["/api/v1/invoices"]
    assert "post" not in schema["paths"]["/api/v1/invoices"]
    assert "get" in schema["paths"]["/api/v1/invoices/{invoice_id}"]
    assert "put" not in schema["paths"]["/api/v1/invoices/{invoice_id}"]
    assert "patch" not in schema["paths"]["/api/v1/invoices/{invoice_id}"]
    assert "delete" not in schema["paths"]["/api/v1/invoices/{invoice_id}"]
