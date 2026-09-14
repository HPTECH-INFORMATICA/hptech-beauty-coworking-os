"""Tenant-scoped read-only persistence for BCOS Billing."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_INVOICE_COLUMNS = """
    id, professional_id, source_usage_id, professional_billing_contract_id,
    billing_cycle_start, billing_cycle_end, manual_closed_at,
    status::text AS status, currency, subtotal_amount, discount_amount,
    total_amount, created_at, updated_at
"""


async def list_invoices(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    professional_id: UUID | None,
    status: str | None,
    limit: int,
    offset: int,
) -> list[Any]:
    result = await session.execute(
        text(
            f"""
            SELECT {_INVOICE_COLUMNS}
            FROM invoices
            WHERE tenant_id = :tenant_id
              AND (:professional_id IS NULL OR professional_id = :professional_id)
              AND (:status IS NULL OR status = CAST(:status AS invoice_status))
            ORDER BY created_at DESC, id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {
            "tenant_id": tenant_id,
            "professional_id": professional_id,
            "status": status,
            "limit": limit,
            "offset": offset,
        },
    )
    return list(result.mappings().all())


async def get_invoice(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    invoice_id: UUID,
) -> Any | None:
    result = await session.execute(
        text(
            f"""
            SELECT {_INVOICE_COLUMNS}
            FROM invoices
            WHERE tenant_id = :tenant_id AND id = :invoice_id
            """
        ),
        {"tenant_id": tenant_id, "invoice_id": invoice_id},
    )
    return result.mappings().one_or_none()


async def list_invoice_items(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    invoice_id: UUID,
) -> list[Any]:
    result = await session.execute(
        text(
            """
            SELECT id, usage_id, item_type::text AS item_type, description,
                   quantity, unit_amount, total_amount, billing_period_start,
                   billing_period_end, related_invoice_item_id, created_at
            FROM invoice_items
            WHERE tenant_id = :tenant_id AND invoice_id = :invoice_id
            ORDER BY created_at ASC, id ASC
            """
        ),
        {"tenant_id": tenant_id, "invoice_id": invoice_id},
    )
    return list(result.mappings().all())


async def confirmed_amount(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    invoice_id: UUID,
):
    result = await session.execute(
        text(
            """
            SELECT COALESCE(SUM(amount), 0)::NUMERIC(12, 2)
            FROM payments
            WHERE tenant_id = :tenant_id
              AND invoice_id = :invoice_id
              AND status = 'CONFIRMED'
            """
        ),
        {"tenant_id": tenant_id, "invoice_id": invoice_id},
    )
    return result.scalar_one()
