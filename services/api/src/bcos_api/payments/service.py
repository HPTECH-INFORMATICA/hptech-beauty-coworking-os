"""Payment application service for BCOS."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.payments.domain import Payment
from bcos_api.payments.repository import (
    confirmed_amount_for_invoice,
    create_confirmed_pix_payment,
    get_payment_by_idempotency_key,
    lock_invoice,
    update_invoice_payment_status,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.rbac import Permission, require_permission


class PaymentNotFound(Exception):
    """Raised when the target Invoice does not exist in the tenant."""


class PaymentConflict(Exception):
    """Raised when a payment violates the current Invoice state."""


class PaymentIdempotencyConflict(Exception):
    """Raised when an idempotency key is reused for another payment."""


def _row_value(row: Any, key: str) -> Any:
    return row._mapping[key]


async def confirm_pix_payment(
    session: AsyncSession,
    *,
    context: TenantContext,
    invoice_id: UUID,
    idempotency_key: str,
    amount: Decimal,
    reference: str | None,
    metadata: dict[str, object],
    paid_at: datetime | None = None,
) -> tuple[Payment, str, Decimal, Decimal, Decimal]:
    """Register one confirmed PIX and recompute Invoice payment state."""

    require_permission(context, Permission.OPERATIONS)

    normalized_key = idempotency_key.strip()
    if not normalized_key:
        raise PaymentConflict("Payment idempotency key cannot be blank.")

    invoice = await lock_invoice(
        session,
        tenant_id=context.tenant_id,
        invoice_id=invoice_id,
    )

    if invoice is None:
        raise PaymentNotFound("Invoice does not exist in the tenant.")

    existing = await get_payment_by_idempotency_key(
        session,
        tenant_id=context.tenant_id,
        idempotency_key=normalized_key,
    )

    if existing is not None:
        if (
            existing.invoice_id != invoice_id
            or existing.amount != amount
            or existing.method.value != "PIX"
            or existing.status.value != "CONFIRMED"
        ):
            raise PaymentIdempotencyConflict(
                "Payment idempotency key is already in use."
            )

        total_amount = Decimal(_row_value(invoice, "total_amount"))
        confirmed_amount = await confirmed_amount_for_invoice(
            session,
            tenant_id=context.tenant_id,
            invoice_id=invoice_id,
        )
        remaining_amount = max(
            Decimal("0.00"),
            total_amount - confirmed_amount,
        )

        return (
            existing,
            str(_row_value(invoice, "status")),
            total_amount,
            confirmed_amount,
            remaining_amount,
        )

    invoice_status = str(_row_value(invoice, "status"))
    currency = str(_row_value(invoice, "currency"))
    total_amount = Decimal(_row_value(invoice, "total_amount"))

    if invoice_status == "CANCELLED":
        raise PaymentConflict("Cancelled Invoice cannot receive payment.")

    if invoice_status == "PAID":
        raise PaymentConflict("Paid Invoice cannot receive another payment.")

    if currency != "BRL":
        raise PaymentConflict("PIX payment requires a BRL Invoice.")

    confirmed_before = await confirmed_amount_for_invoice(
        session,
        tenant_id=context.tenant_id,
        invoice_id=invoice_id,
    )

    confirmed_after = confirmed_before + amount

    if confirmed_after > total_amount:
        raise PaymentConflict("Payment exceeds Invoice remaining amount.")

    actual_paid_at = paid_at if paid_at is not None else datetime.now(UTC)

    if actual_paid_at.tzinfo is None or actual_paid_at.utcoffset() is None:
        raise PaymentConflict("paid_at must be timezone-aware.")

    payment = await create_confirmed_pix_payment(
        session,
        tenant_id=context.tenant_id,
        invoice_id=invoice_id,
        idempotency_key=normalized_key,
        amount=amount,
        reference=reference,
        metadata=metadata,
        paid_at=actual_paid_at,
    )

    resulting_status = (
        "PAID"
        if confirmed_after == total_amount
        else "PARTIALLY_PAID"
    )

    await update_invoice_payment_status(
        session,
        tenant_id=context.tenant_id,
        invoice_id=invoice_id,
        invoice_status=resulting_status,
    )

    remaining_amount = total_amount - confirmed_after

    return (
        payment,
        resulting_status,
        total_amount,
        confirmed_after,
        remaining_amount,
    )