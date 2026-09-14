"""Application service for the BCOS Billing boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.audit.repository import create_audit_log
from bcos_api.billing import repository
from bcos_api.billing.schemas import InvoiceDetail, InvoiceItem, InvoiceStatus, InvoiceSummary
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.rbac import Permission, require_permission


class InvoiceNotFound(Exception):
    """Raised when an Invoice is absent from the authorized tenant."""


class InvoiceLifecycleConflict(Exception):
    """Raised when an Invoice is outside the approved T29 close boundary."""


def _summary(row) -> InvoiceSummary:
    return InvoiceSummary(**dict(row))


def _is_manual_accumulated(row) -> bool:
    return (
        row["source_usage_id"] is None
        and row["professional_billing_contract_id"] is not None
        and row["billing_cycle_start"] is None
        and row["billing_cycle_end"] is None
    )


async def list_tenant_invoices(
    session: AsyncSession,
    *,
    context: TenantContext,
    professional_id: UUID | None,
    status: InvoiceStatus | None,
    limit: int,
    offset: int,
) -> list[InvoiceSummary]:
    require_permission(context, Permission.OPERATIONS)
    rows = await repository.list_invoices(
        session,
        tenant_id=context.tenant_id,
        professional_id=professional_id,
        status=status.value if status is not None else None,
        limit=limit,
        offset=offset,
    )
    return [_summary(row) for row in rows]


async def get_tenant_invoice(
    session: AsyncSession,
    *,
    context: TenantContext,
    invoice_id: UUID,
) -> InvoiceDetail:
    require_permission(context, Permission.OPERATIONS)
    row = await repository.get_invoice(
        session,
        tenant_id=context.tenant_id,
        invoice_id=invoice_id,
    )
    if row is None:
        raise InvoiceNotFound("Invoice does not exist in the tenant.")

    item_rows = await repository.list_invoice_items(
        session,
        tenant_id=context.tenant_id,
        invoice_id=invoice_id,
    )
    paid = Decimal(
        await repository.confirmed_amount(
            session,
            tenant_id=context.tenant_id,
            invoice_id=invoice_id,
        )
    )
    total = Decimal(row["total_amount"])
    if paid > total:
        raise RuntimeError("Confirmed Payment evidence exceeds Invoice total.")

    summary = _summary(row)
    return InvoiceDetail(
        **summary.model_dump(),
        items=[InvoiceItem(**dict(item)) for item in item_rows],
        confirmed_amount=paid,
        remaining_amount=total - paid,
    )


async def close_tenant_manual_invoice(
    session: AsyncSession,
    *,
    context: TenantContext,
    invoice_id: UUID,
) -> InvoiceSummary:
    """Close one MANUAL accumulated Invoice under approved T29/T30."""

    require_permission(context, Permission.OPERATIONS)
    row = await repository.lock_invoice(
        session,
        tenant_id=context.tenant_id,
        invoice_id=invoice_id,
    )
    if row is None:
        raise InvoiceNotFound("Invoice does not exist in the tenant.")
    if not _is_manual_accumulated(row):
        raise InvoiceLifecycleConflict("Only MANUAL accumulated Invoices may be closed.")

    if row["manual_closed_at"] is not None:
        return _summary(row)

    invoice_status = InvoiceStatus(row["status"])
    if invoice_status not in {InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID}:
        raise InvoiceLifecycleConflict(
            f"Invoice status {invoice_status.value} is not eligible for MANUAL closure."
        )

    closed_at = datetime.now(UTC)
    closed_row = await repository.close_manual_invoice(
        session,
        tenant_id=context.tenant_id,
        invoice_id=invoice_id,
        closed_at=closed_at,
    )
    persisted_closed_at = closed_row["manual_closed_at"]
    await create_audit_log(
        session,
        tenant_id=context.tenant_id,
        actor_external_user_id=context.external_user_id,
        action="INVOICE_MANUAL_CLOSED",
        entity_type="INVOICE",
        entity_id=invoice_id,
        metadata={
            "manual_closed_at": persisted_closed_at.astimezone(UTC).isoformat(),
            "status": invoice_status.value,
        },
    )
    return _summary(closed_row)
