"""Application service for the BCOS Billing read boundary."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.billing import repository
from bcos_api.billing.schemas import InvoiceDetail, InvoiceItem, InvoiceStatus, InvoiceSummary
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.rbac import Permission, require_permission


class InvoiceNotFound(Exception):
    """Raised when an Invoice is absent from the authorized tenant."""


def _summary(row) -> InvoiceSummary:
    return InvoiceSummary(**dict(row))


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
