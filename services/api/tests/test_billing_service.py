from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from bcos_api.billing.schemas import InvoiceStatus
from bcos_api.billing.service import InvoiceNotFound, get_tenant_invoice, list_tenant_invoices
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.rbac import PermissionDenied


def context(role: MembershipRole = MembershipRole.OWNER) -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        membership_id=uuid4(),
        external_user_id="identity:test",
        role=role,
    )


def invoice_row(ctx: TenantContext, *, total: str = "100.00") -> dict[str, object]:
    now = datetime(2026, 9, 14, 15, 0, tzinfo=UTC)
    return {
        "id": uuid4(),
        "professional_id": uuid4(),
        "source_usage_id": uuid4(),
        "professional_billing_contract_id": None,
        "billing_cycle_start": None,
        "billing_cycle_end": None,
        "manual_closed_at": None,
        "status": "OPEN",
        "currency": "BRL",
        "subtotal_amount": Decimal(total),
        "discount_amount": Decimal("0.00"),
        "total_amount": Decimal(total),
        "created_at": now,
        "updated_at": now,
    }


@pytest.mark.asyncio
async def test_list_requires_operations_and_preserves_filters(monkeypatch) -> None:
    ctx = context()
    row = invoice_row(ctx)
    captured: dict[str, object] = {}

    async def fake_list(session, **kwargs):
        captured.update(kwargs)
        return [row]

    monkeypatch.setattr("bcos_api.billing.repository.list_invoices", fake_list)
    result = await list_tenant_invoices(
        object(), context=ctx, professional_id=row["professional_id"],
        status=InvoiceStatus.OPEN, limit=25, offset=50,
    )
    assert result[0].id == row["id"]
    assert captured["tenant_id"] == ctx.tenant_id
    assert captured["status"] == "OPEN"
    assert captured["limit"] == 25
    assert captured["offset"] == 50


@pytest.mark.asyncio
async def test_professional_fails_closed_before_repository(monkeypatch) -> None:
    called = False

    async def fake_list(*args, **kwargs):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr("bcos_api.billing.repository.list_invoices", fake_list)
    with pytest.raises(PermissionDenied):
        await list_tenant_invoices(
            object(), context=context(MembershipRole.PROFESSIONAL),
            professional_id=None, status=None, limit=50, offset=0,
        )
    assert called is False


@pytest.mark.asyncio
async def test_detail_is_tenant_scoped_and_projects_payments(monkeypatch) -> None:
    ctx = context()
    row = invoice_row(ctx)
    captured: list[tuple[str, object]] = []

    async def fake_get(session, **kwargs):
        captured.append(("invoice", kwargs["tenant_id"]))
        return row

    async def fake_items(session, **kwargs):
        captured.append(("items", kwargs["tenant_id"]))
        return []

    async def fake_paid(session, **kwargs):
        captured.append(("payments", kwargs["tenant_id"]))
        return Decimal("40.00")

    monkeypatch.setattr("bcos_api.billing.repository.get_invoice", fake_get)
    monkeypatch.setattr("bcos_api.billing.repository.list_invoice_items", fake_items)
    monkeypatch.setattr("bcos_api.billing.repository.confirmed_amount", fake_paid)

    detail = await get_tenant_invoice(object(), context=ctx, invoice_id=row["id"])
    assert detail.confirmed_amount == Decimal("40.00")
    assert detail.remaining_amount == Decimal("60.00")
    assert all(tenant_id == ctx.tenant_id for _, tenant_id in captured)


@pytest.mark.asyncio
async def test_detail_hides_absent_or_cross_tenant_invoice(monkeypatch) -> None:
    async def fake_get(session, **kwargs):
        return None

    monkeypatch.setattr("bcos_api.billing.repository.get_invoice", fake_get)
    with pytest.raises(InvoiceNotFound):
        await get_tenant_invoice(object(), context=context(), invoice_id=uuid4())


@pytest.mark.asyncio
async def test_detail_fails_closed_if_confirmed_evidence_exceeds_total(monkeypatch) -> None:
    ctx = context()
    row = invoice_row(ctx)

    async def fake_get(session, **kwargs):
        return row

    async def fake_items(session, **kwargs):
        return []

    async def fake_paid(session, **kwargs):
        return Decimal("100.01")

    monkeypatch.setattr("bcos_api.billing.repository.get_invoice", fake_get)
    monkeypatch.setattr("bcos_api.billing.repository.list_invoice_items", fake_items)
    monkeypatch.setattr("bcos_api.billing.repository.confirmed_amount", fake_paid)
    with pytest.raises(RuntimeError, match="exceeds Invoice total"):
        await get_tenant_invoice(object(), context=ctx, invoice_id=row["id"])
