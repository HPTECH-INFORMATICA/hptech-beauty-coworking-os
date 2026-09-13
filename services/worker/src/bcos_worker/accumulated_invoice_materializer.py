"""Financial materialization for BCOS accumulated open invoices."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_worker.billing_cycle import BillingCycleResolutionError, resolve_billing_cycle
from bcos_worker.financial_effects import (
    FinancialEffect,
    FinancialEffectType,
    calculate_usage_financial_effects,
)
from bcos_worker.invoice_repository import (
    AccumulatedInvoiceIdentity,
    InvoiceMaterializationError,
    get_or_create_accumulated_invoice,
)
from bcos_worker.overtime_money import quantize_money
from bcos_worker.pricing_context import UsagePricingContext


@dataclass(frozen=True, slots=True)
class AccumulatedMaterializationResult:
    invoice: AccumulatedInvoiceIdentity
    subtotal_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal


def _consolidate_overtime(
    context: UsagePricingContext,
    overtime_effects: tuple[FinancialEffect, ...],
) -> tuple[FinancialEffect, dict[str, Any]] | None:
    if not overtime_effects:
        return None

    completed_minutes = sum(
        (effect.quantity for effect in overtime_effects),
        Decimal("0"),
    )
    total_amount = quantize_money(
        sum((effect.total_amount for effect in overtime_effects), Decimal("0"))
    )
    hourly_amount = quantize_money(
        context.pricing_rule.overtime.hourly_price_amount
    )

    return (
        FinancialEffect(
            item_type=FinancialEffectType.OVERTIME,
            description="Overtime",
            quantity=completed_minutes,
            unit_amount=hourly_amount,
            total_amount=total_amount,
        ),
        {
            "forgiveness_allowed": context.pricing_rule.overtime.forgiveness_allowed,
            "reception_segments": [
                {
                    "segment": segment.reception_segment,
                    "completed_minutes": int(segment.quantity),
                    "amount": format(segment.total_amount, ".2f"),
                }
                for segment in overtime_effects
            ],
        },
    )


async def _ensure_nonsegmented_invoice_item(
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
                metadata,
                billing_period_start,
                billing_period_end
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
                CAST(:metadata AS jsonb),
                NULL,
                NULL
            )
            ON CONFLICT (tenant_id, usage_id, item_type)
                WHERE usage_id IS NOT NULL
                  AND billing_period_start IS NULL
                  AND billing_period_end IS NULL
            DO NOTHING
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
            "metadata": json.dumps(metadata, sort_keys=True, separators=(",", ":")),
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
                item_type::text AS item_type,
                description,
                quantity,
                unit_amount,
                total_amount,
                metadata,
                billing_period_start,
                billing_period_end
            FROM invoice_items
            WHERE tenant_id = :tenant_id
              AND usage_id = :usage_id
              AND item_type = CAST(:item_type AS invoice_item_type)
              AND billing_period_start IS NULL
              AND billing_period_end IS NULL
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
            "accumulated InvoiceItem identity is missing or ambiguous"
        )

    row = rows[0]
    if row["invoice_id"] != invoice_id:
        raise InvoiceMaterializationError(
            "existing accumulated InvoiceItem belongs to another Invoice"
        )
    if row["usage_id"] != usage_id:
        raise InvoiceMaterializationError(
            "existing accumulated InvoiceItem belongs to another Usage"
        )
    if row["item_type"] != effect.item_type.value:
        raise InvoiceMaterializationError(
            "existing accumulated InvoiceItem type differs from expected value"
        )
    if row["description"] != effect.description:
        raise InvoiceMaterializationError(
            "existing accumulated InvoiceItem description differs from expected value"
        )
    if Decimal(row["quantity"]) != effect.quantity:
        raise InvoiceMaterializationError(
            "existing accumulated InvoiceItem quantity differs from expected value"
        )
    if Decimal(row["unit_amount"]) != effect.unit_amount:
        raise InvoiceMaterializationError(
            "existing accumulated InvoiceItem unit amount differs from expected value"
        )
    if Decimal(row["total_amount"]) != effect.total_amount:
        raise InvoiceMaterializationError(
            "existing accumulated InvoiceItem total differs from expected value"
        )
    if dict(row["metadata"]) != metadata:
        raise InvoiceMaterializationError(
            "existing accumulated InvoiceItem metadata differs from expected value"
        )
    if row["billing_period_start"] is not None or row["billing_period_end"] is not None:
        raise InvoiceMaterializationError(
            "nonsegmented accumulated InvoiceItem has Billing period boundaries"
        )


async def _recalculate_invoice_totals(
    session: AsyncSession,
    *,
    invoice: AccumulatedInvoiceIdentity,
) -> tuple[Decimal, Decimal, Decimal]:
    totals_result = await session.execute(
        text(
            """
            SELECT
                COALESCE(SUM(CASE WHEN item_type <> 'DISCOUNT' THEN total_amount ELSE 0 END), 0) AS subtotal_amount,
                COALESCE(SUM(CASE WHEN item_type = 'DISCOUNT' THEN ABS(total_amount) ELSE 0 END), 0) AS discount_amount
            FROM invoice_items
            WHERE tenant_id = :tenant_id
              AND invoice_id = :invoice_id
            """
        ),
        {
            "tenant_id": invoice.tenant_id,
            "invoice_id": invoice.id,
        },
    )
    totals = totals_result.mappings().one()

    subtotal_amount = quantize_money(Decimal(totals["subtotal_amount"]))
    discount_amount = quantize_money(Decimal(totals["discount_amount"]))
    total_amount = quantize_money(subtotal_amount - discount_amount)

    if total_amount < Decimal("0"):
        raise InvoiceMaterializationError(
            "accumulated Invoice discounts exceed subtotal"
        )

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
              AND professional_billing_contract_id = :contract_id
              AND source_usage_id IS NULL
              AND status = 'OPEN'
            RETURNING id
            """
        ),
        {
            "invoice_id": invoice.id,
            "tenant_id": invoice.tenant_id,
            "professional_id": invoice.professional_id,
            "contract_id": invoice.professional_billing_contract_id,
            "subtotal_amount": subtotal_amount,
            "discount_amount": discount_amount,
            "total_amount": total_amount,
        },
    )

    if update_result.scalar_one_or_none() is None:
        raise InvoiceMaterializationError(
            "accumulated Invoice totals could not be updated"
        )

    return subtotal_amount, discount_amount, total_amount


async def materialize_accumulated_invoice(
    session: AsyncSession,
    context: UsagePricingContext,
) -> AccumulatedMaterializationResult:
    """Materialize one completed Usage into an accumulated open Invoice."""

    contract = context.professional_billing_contract
    if contract.invoice_mode != "ACCUMULATED_OPEN_INVOICE":
        raise InvoiceMaterializationError(
            "accumulated materializer received a non-accumulated billing contract"
        )

    allocation_policy = contract.cycle_allocation_policy
    if allocation_policy not in {"USAGE_COMPLETION", "FIXED_CUTOFF_SPLIT"}:
        raise InvoiceMaterializationError(
            "accumulated Billing contract has unsupported allocation policy"
        )

    if allocation_policy == "FIXED_CUTOFF_SPLIT":
        raise InvoiceMaterializationError(
            "FIXED_CUTOFF_SPLIT requires deterministic temporal financial segmentation"
        )

    try:
        cycle = resolve_billing_cycle(
            contract=contract,
            unit_timezone=context.unit_timezone,
            reference_instant=context.checked_out_at,
        )
    except BillingCycleResolutionError as exc:
        raise InvoiceMaterializationError(
            f"accumulated Billing cycle could not be resolved: {exc}"
        ) from exc

    invoice = await get_or_create_accumulated_invoice(
        session,
        tenant_id=context.tenant_id,
        professional_id=context.professional_id,
        professional_billing_contract_id=contract.id,
        cycle=cycle,
    )

    effects = calculate_usage_financial_effects(context)

    await _ensure_nonsegmented_invoice_item(
        session,
        invoice_id=invoice.id,
        tenant_id=context.tenant_id,
        usage_id=context.usage_id,
        effect=effects.base_lease,
        metadata={},
    )

    overtime = _consolidate_overtime(context, effects.overtime)
    if overtime is not None:
        overtime_effect, overtime_metadata = overtime
        await _ensure_nonsegmented_invoice_item(
            session,
            invoice_id=invoice.id,
            tenant_id=context.tenant_id,
            usage_id=context.usage_id,
            effect=overtime_effect,
            metadata=overtime_metadata,
        )

    subtotal_amount, discount_amount, total_amount = await _recalculate_invoice_totals(
        session,
        invoice=invoice,
    )

    return AccumulatedMaterializationResult(
        invoice=invoice,
        subtotal_amount=subtotal_amount,
        discount_amount=discount_amount,
        total_amount=total_amount,
    )
