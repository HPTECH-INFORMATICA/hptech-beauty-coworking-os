"""Persistence operations for BCOS Payments."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.payments.domain import (
    Payment,
    PaymentMethod,
    PaymentStatus,
)


def _payment_from_row(row: Any) -> Payment:
    mapping = row._mapping

    return Payment(
        id=mapping["id"],
        tenant_id=mapping["tenant_id"],
        invoice_id=mapping["invoice_id"],
        idempotency_key=mapping["idempotency_key"],
        method=PaymentMethod(mapping["method"]),
        status=PaymentStatus(mapping["status"]),
        currency=mapping["currency"],
        amount=mapping["amount"],
        reference=mapping["reference"],
        metadata=mapping["metadata"],
        paid_at=mapping["paid_at"],
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
    )


async def get_payment_by_idempotency_key(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    idempotency_key: str,
) -> Payment | None:
    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                invoice_id,
                idempotency_key,
                method,
                status,
                currency,
                amount,
                reference,
                metadata,
                paid_at,
                created_at,
                updated_at
            FROM payments
            WHERE tenant_id = :tenant_id
              AND idempotency_key = :idempotency_key
            """
        ),
        {
            "tenant_id": tenant_id,
            "idempotency_key": idempotency_key,
        },
    )

    row = result.first()
    return _payment_from_row(row) if row is not None else None


async def lock_invoice(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    invoice_id: UUID,
) -> Any | None:
    result = await session.execute(
        text(
            """
            SELECT
                id,
                status,
                currency,
                total_amount
            FROM invoices
            WHERE tenant_id = :tenant_id
              AND id = :invoice_id
            FOR UPDATE
            """
        ),
        {
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
        },
    )

    return result.first()


async def confirmed_amount_for_invoice(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    invoice_id: UUID,
) -> Decimal:
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
        {
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
        },
    )

    value = result.scalar_one()
    return Decimal(value)


async def create_confirmed_pix_payment(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    invoice_id: UUID,
    idempotency_key: str,
    amount: Decimal,
    reference: str | None,
    metadata: dict[str, object],
    paid_at: datetime,
) -> Payment:
    result = await session.execute(
        text(
            """
            INSERT INTO payments (
                tenant_id,
                invoice_id,
                idempotency_key,
                method,
                status,
                currency,
                amount,
                reference,
                metadata,
                paid_at
            )
            VALUES (
                :tenant_id,
                :invoice_id,
                :idempotency_key,
                'PIX',
                'CONFIRMED',
                'BRL',
                :amount,
                :reference,
                CAST(:metadata AS JSONB),
                :paid_at
            )
            RETURNING
                id,
                tenant_id,
                invoice_id,
                idempotency_key,
                method,
                status,
                currency,
                amount,
                reference,
                metadata,
                paid_at,
                created_at,
                updated_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
            "idempotency_key": idempotency_key,
            "amount": amount,
            "reference": reference,
            "metadata": __import__("json").dumps(metadata),
            "paid_at": paid_at,
        },
    )

    row = result.one()
    return _payment_from_row(row)


async def update_invoice_payment_status(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    invoice_id: UUID,
    invoice_status: str,
) -> None:
    await session.execute(
        text(
            """
            UPDATE invoices
            SET
                status = CAST(:invoice_status AS invoice_status),
                updated_at = now()
            WHERE tenant_id = :tenant_id
              AND id = :invoice_id
            """
        ),
        {
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
            "invoice_status": invoice_status,
        },
    )