from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from bcos_api.billing.schemas import InvoiceStatus
from bcos_api.billing.service import (
    InvoiceLifecycleConflict,
    InvoiceNotFound,
    close_tenant_manual_invoice,
    get_tenant_invoice,
    list_tenant_invoices,
)
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


def invoice_row(
    ctx: TenantContext,
    *,
    total: str = "100.00",
    manual: bool = False,
    status: str = "OPEN",
    closed_at: datetime | None = None,
) -> dict[str, object]:
    now = datetime(2026, 9, 14, 15, 0, tzinfo=UTC)
    return {
        "id": uuid4(),
        "professional_id": uuid4(),
        "source_usage_id": None if manual else uuid4(),
        "professional_billing_contract_id": uuid4() if manual else None,
        "billing_cycle_start": None,
        "billing_cycle_end": None,
        "manual_closed_at": closed_at,
        "status": status,
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


@pytest.mark.asyncio
@pytest.mark.parametrize("financial_status", ["OPEN", "PARTIALLY_PAID"])
async def test_close_manual_invoice_persists_boundary_and_audit(
    monkeypatch, financial_status: str
) -> None:
    ctx = context()
    row = invoice_row(ctx, manual=True, status=financial_status)
    closed_at = datetime(2026, 9, 14, 22, 0, tzinfo=UTC)
    closed = {**row, "manual_closed_at": closed_at, "updated_at": closed_at}
    audit: dict[str, object] = {}

    async def fake_lock(session, **kwargs):
        assert kwargs["tenant_id"] == ctx.tenant_id
        return row

    async def fake_close(session, **kwargs):
        assert kwargs["tenant_id"] == ctx.tenant_id
        return closed

    async def fake_audit(session, **kwargs):
        audit.update(kwargs)

    monkeypatch.setattr("bcos_api.billing.repository.lock_invoice", fake_lock)
    monkeypatch.setattr("bcos_api.billing.repository.close_manual_invoice", fake_close)
    monkeypatch.setattr("bcos_api.billing.service.create_audit_log", fake_audit)

    result = await close_tenant_manual_invoice(object(), context=ctx, invoice_id=row["id"])
    assert result.manual_closed_at == closed_at
    assert audit["tenant_id"] == ctx.tenant_id
    assert audit["actor_external_user_id"] == ctx.external_user_id
    assert audit["action"] == "INVOICE_MANUAL_CLOSED"
    assert audit["entity_type"] == "INVOICE"
    assert audit["entity_id"] == row["id"]
    assert audit["metadata"] == {
        "manual_closed_at": closed_at.isoformat(),
        "status": financial_status,
    }


@pytest.mark.asyncio
async def test_close_is_idempotent_without_duplicate_mutation_or_audit(monkeypatch) -> None:
    ctx = context()
    original = datetime(2026, 9, 14, 21, 0, tzinfo=UTC)
    row = invoice_row(ctx, manual=True, closed_at=original)
    mutated = False
    audited = False

    async def fake_lock(session, **kwargs):
        return row

    async def fake_close(*args, **kwargs):
        nonlocal mutated
        mutated = True

    async def fake_audit(*args, **kwargs):
        nonlocal audited
        audited = True

    monkeypatch.setattr("bcos_api.billing.repository.lock_invoice", fake_lock)
    monkeypatch.setattr("bcos_api.billing.repository.close_manual_invoice", fake_close)
    monkeypatch.setattr("bcos_api.billing.service.create_audit_log", fake_audit)

    result = await close_tenant_manual_invoice(object(), context=ctx, invoice_id=row["id"])
    assert result.manual_closed_at == original
    assert mutated is False
    assert audited is False


@pytest.mark.asyncio
@pytest.mark.parametrize("financial_status", ["PAID", "CANCELLED"])
async def test_close_rejects_ineligible_financial_status(monkeypatch, financial_status) -> None:
    ctx = context()
    row = invoice_row(ctx, manual=True, status=financial_status)

    async def fake_lock(session, **kwargs):
        return row

    monkeypatch.setattr("bcos_api.billing.repository.lock_invoice", fake_lock)
    with pytest.raises(InvoiceLifecycleConflict, match="not eligible"):
        await close_tenant_manual_invoice(object(), context=ctx, invoice_id=row["id"])


@pytest.mark.asyncio
async def test_close_rejects_per_usage_or_automatic_identity(monkeypatch) -> None:
    ctx = context()
    row = invoice_row(ctx)

    async def fake_lock(session, **kwargs):
        return row

    monkeypatch.setattr("bcos_api.billing.repository.lock_invoice", fake_lock)
    with pytest.raises(InvoiceLifecycleConflict, match="Only MANUAL"):
        await close_tenant_manual_invoice(object(), context=ctx, invoice_id=row["id"])


@pytest.mark.asyncio
async def test_professional_cannot_close_before_lock(monkeypatch) -> None:
    called = False

    async def fake_lock(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("bcos_api.billing.repository.lock_invoice", fake_lock)
    with pytest.raises(PermissionDenied):
        await close_tenant_manual_invoice(
            object(), context=context(MembershipRole.PROFESSIONAL), invoice_id=uuid4()
        )
    assert called is False
