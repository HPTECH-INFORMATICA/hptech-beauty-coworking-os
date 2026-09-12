"""Financial materialization for BCOS PER_USAGE invoices."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_worker.financial_effects import (
    FinancialEffect,
    FinancialEffectType,
    calculate_usage_financial_effects,
)
from bcos_worker.invoice_repository import (
    InvoiceIdentity,
    InvoiceMaterializationError,
    get_or_create_per_usage_invoice,
)
from bcos_worker.overtime_money import quantize_money
from bcos_worker.pricing_context import UsagePricingContext


@dataclass(frozen=True, slots=True)
class PerUsageMaterializationResult:
    invoice: InvoiceIdentity
    subtotal_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal


async def _ensure_invoice_item(
    session: AsyncSession,
    *,
    invoice_id: UUID,
    tenant_id: UUID,
    usage_id: UUID,
    effect: FinancialEffect,
    metadata: dict[str, Any],
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO invoice_items (
                tenant_id,
                invoice_id,
                usage_id,
                item_type,
                description,
                quantity,
                unit_amount,
                total_amount,
                metadata
            )
            VALUES (
                :tenant_id,
                :invoice_id,
                :usage_id,
                :item_type,
                :description,
                :quantity,
                :unit_amount,
                :total_amount,
                CAST(:metadata AS jsonb)
            )
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
            "usage_id": usage_id,
            "item_type": effect.item_type.value,
            "description": effect.description,
            "quantity": effect.quantity,
            "unit_amount": effect.unit_amount,
            "total_amount": effect.total_amount,
            "metadata": json.dumps(
                metadata,
                sort_keys=True,
                separators=(",", ":"),
            ),
        },
    )

    result = await session.execute(
        text(
            """
            SELECT
                id,
                invoice_id,
                tenant_id,
                usage_id,
                item_type,
                description,
                quantity,
                unit_amount,
                total_amount,
                metadata
            FROM invoice_items
            WHERE tenant_id = :tenant_id
              AND usage_id = :usage_id
              AND item_type = :item_type
            ORDER BY created_at, id
            """
        ),
        {
            "tenant_id": tenant_id,
            "usage_id": usage_id,
            "item_type": effect.item_type.value,
        },
    )

    rows = result.mappings().all()

    if len(rows) != 1:
        raise InvoiceMaterializationError(
            "PER_USAGE InvoiceItem identity is missing or ambiguous"
        )

    row = rows[0]

    if row["invoice_id"] != invoice_id:
        raise InvoiceMaterializationError(
            "existing PER_USAGE InvoiceItem belongs to another Invoice"
        )

    if row["usage_id"] != usage_id:
        raise InvoiceMaterializationError(
            "existing PER_USAGE InvoiceItem belongs to another Usage"
        )

    if row["description"] != effect.description:
        raise InvoiceMaterializationError(
            "existing PER_USAGE InvoiceItem description differs from expected value"
        )

    if Decimal(row["quantity"]) != effect.quantity:
        raise InvoiceMaterializationError(
            "existing PER_USAGE InvoiceItem quantity differs from expected value"
        )

    if Decimal(row["unit_amount"]) != effect.unit_amount:
        raise InvoiceMaterializationError(
            "existing PER_USAGE InvoiceItem unit amount differs from expected value"
        )

    if Decimal(row["total_amount"]) != effect.total_amount:
        raise InvoiceMaterializationError(
            "existing PER_USAGE InvoiceItem total differs from expected value"
        )

    if dict(row["metadata"]) != metadata:
        raise InvoiceMaterializationError(
            "existing PER_USAGE InvoiceItem metadata differs from expected value"
        )


def _consolidate_overtime(
    context: UsagePricingContext,
    overtime_effects: tuple[FinancialEffect, ...],
) -> tuple[FinancialEffect, dict[str, Any]] | None:
    if not overtime_effects:
        return None

    completed_minutes = sum(
        (
            effect.quantity
            for effect in overtime_effects
        ),
        Decimal("0"),
    )

    total_amount = quantize_money(
        sum(
            (
                effect.total_amount
                for effect in overtime_effects
            ),
            Decimal("0"),
        )
    )

    hourly_amount = quantize_money(
        context.pricing_rule.overtime.hourly_price_amount
    )

    effect = FinancialEffect(
        item_type=FinancialEffectType.OVERTIME,
        description="Overtime",
        quantity=completed_minutes,
        unit_amount=hourly_amount,
        total_amount=total_amount,
    )

    metadata: dict[str, Any] = {
        "forgiveness_allowed": (
            context.pricing_rule.overtime.forgiveness_allowed
        ),
        "reception_segments": [
            {
                "segment": segment.reception_segment,
                "completed_minutes": int(segment.quantity),
                "amount": format(segment.total_amount, ".2f"),
            }
            for segment in overtime_effects
        ],
    }

    return effect, metadata


async def materialize_per_usage_invoice(
    session: AsyncSession,
    context: UsagePricingContext,
) -> PerUsageMaterializationResult:
    """Materialize one completed Usage into its idempotent PER_USAGE Invoice."""

    contract = context.professional_billing_contract

    if contract.invoice_mode != "PER_USAGE":
        raise InvoiceMaterializationError(
            "PER_USAGE materializer received a non-PER_USAGE billing contract"
        )

    effects = calculate_usage_financial_effects(context)

    invoice = await get_or_create_per_usage_invoice(
        session,
        tenant_id=context.tenant_id,
        professional_id=context.professional_id,
        usage_id=context.usage_id,
    )

    await _ensure_invoice_item(
        session,
        invoice_id=invoice.id,
        tenant_id=context.tenant_id,
        usage_id=context.usage_id,
        effect=effects.base_lease,
        metadata={},
    )

    overtime = _consolidate_overtime(
        context,
        effects.overtime,
    )

    overtime_amount = Decimal("0")

    if overtime is not None:
        overtime_effect, overtime_metadata = overtime

        await _ensure_invoice_item(
            session,
            invoice_id=invoice.id,
            tenant_id=context.tenant_id,
            usage_id=context.usage_id,
            effect=overtime_effect,
            metadata=overtime_metadata,
        )

        overtime_amount = overtime_effect.total_amount

    subtotal_amount = quantize_money(
        effects.base_lease.total_amount + overtime_amount
    )
    discount_amount = Decimal("0.00")
    total_amount = subtotal_amount

    update_result = await session.execute(
        text(
            """
            UPDATE invoices
            SET
                subtotal_amount = :subtotal_amount,
                discount_amount = :discount_amount,
                total_amount = :total_amount,
                updated_at = now()
            WHERE id = :invoice_id
              AND tenant_id = :tenant_id
              AND professional_id = :professional_id
              AND source_usage_id = :usage_id
            RETURNING id
            """
        ),
        {
            "invoice_id": invoice.id,
            "tenant_id": context.tenant_id,
            "professional_id": context.professional_id,
            "usage_id": context.usage_id,
            "subtotal_amount": subtotal_amount,
            "discount_amount": discount_amount,
            "total_amount": total_amount,
        },
    )

    if update_result.scalar_one_or_none() is None:
        raise InvoiceMaterializationError(
            "PER_USAGE Invoice totals could not be updated"
        )

    return PerUsageMaterializationResult(
        invoice=invoice,
        subtotal_amount=subtotal_amount,
        discount_amount=discount_amount,
        total_amount=total_amount,
    )