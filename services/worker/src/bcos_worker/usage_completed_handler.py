"""Transactional Billing handler for the USAGE_COMPLETED Outbox event."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_worker.dispatcher import UsageCompletedEvent
from bcos_worker.invoice_materializer import materialize_per_usage_invoice
from bcos_worker.invoice_repository import InvoiceMaterializationError
from bcos_worker.outbox import OutboxEvent
from bcos_worker.pricing_context import hydrate_usage_pricing_context


async def handle_usage_completed(
    session: AsyncSession,
    event: OutboxEvent,
    usage_completed: UsageCompletedEvent,
) -> None:
    """Materialize Billing for one completed Usage inside the consumer transaction."""

    context = await hydrate_usage_pricing_context(
        session,
        tenant_id=event.tenant_id,
        usage_id=usage_completed.usage_id,
    )

    if context.tenant_id != event.tenant_id:
        raise InvoiceMaterializationError(
            "USAGE_COMPLETED hydrated context belongs to another tenant"
        )

    if context.usage_id != usage_completed.usage_id:
        raise InvoiceMaterializationError(
            "USAGE_COMPLETED hydrated context belongs to another Usage"
        )

    if context.usage_status != "COMPLETED":
        raise InvoiceMaterializationError(
            "USAGE_COMPLETED Billing requires a completed Usage"
        )

    if context.checked_out_at != usage_completed.checked_out_at:
        raise InvoiceMaterializationError(
            "USAGE_COMPLETED payload checked_out_at differs from authoritative Usage"
        )

    invoice_mode = context.professional_billing_contract.invoice_mode

    if invoice_mode == "PER_USAGE":
        await materialize_per_usage_invoice(
            session,
            context,
        )
        return

    if invoice_mode == "ACCUMULATED_OPEN_INVOICE":
        raise InvoiceMaterializationError(
            "ACCUMULATED_OPEN_INVOICE materialization is not implemented yet"
        )

    raise InvoiceMaterializationError(
        f"Unsupported invoice materialization mode: {invoice_mode}"
    )