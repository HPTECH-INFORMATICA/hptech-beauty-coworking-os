"""Deterministic FIXED_CUTOFF_SPLIT planning for accumulated Billing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from bcos_worker.billing_cycle import (
    BillingCycle,
    BillingCycleResolutionError,
    resolve_billing_cycle,
)
from bcos_worker.financial_effects import FinancialEffect, FinancialEffectType
from bcos_worker.overtime_money import calculate_overtime_amount, quantize_money
from bcos_worker.pricing_context import UsagePricingContext


class FixedCutoffSplitError(RuntimeError):
    """Raised when fixed-cutoff financial segmentation is not deterministic."""


@dataclass(frozen=True, slots=True)
class AllocatedFinancialEffect:
    cycle: BillingCycle
    effect: FinancialEffect


def _cycle_for(
    context: UsagePricingContext,
    reference: datetime,
) -> BillingCycle:
    try:
        cycle = resolve_billing_cycle(
            contract=context.professional_billing_contract,
            unit_timezone=context.unit_timezone,
            reference_instant=reference,
        )
    except BillingCycleResolutionError as exc:
        raise FixedCutoffSplitError(str(exc)) from exc

    if cycle is None:
        raise FixedCutoffSplitError(
            "FIXED_CUTOFF_SPLIT requires an automatic Billing lifecycle"
        )
    return cycle


def _segment_overtime(
    context: UsagePricingContext,
    effect: FinancialEffect,
    *,
    start: datetime,
    end: datetime,
) -> FinancialEffect | None:
    if start >= end:
        return None

    completed_minutes = int((end - start).total_seconds()) // 60
    if completed_minutes <= 0:
        return None

    rule = context.pricing_rule.overtime
    money = calculate_overtime_amount(
        hourly_price_amount=rule.hourly_price_amount,
        completed_minutes=completed_minutes,
        proportional_until_minutes=rule.proportional_until_minutes,
        full_hour_from_minutes=rule.full_hour_from_minutes,
    )

    return FinancialEffect(
        item_type=FinancialEffectType.OVERTIME,
        description=effect.description,
        quantity=Decimal(completed_minutes),
        unit_amount=quantize_money(rule.hourly_price_amount),
        total_amount=money.amount,
        reception_segment=effect.reception_segment,
        billing_period_start=start,
        billing_period_end=end,
    )


def allocate_fixed_cutoff_overtime(
    context: UsagePricingContext,
    effect: FinancialEffect,
) -> tuple[AllocatedFinancialEffect, ...]:
    """Allocate one approved OVERTIME effect across at most one lifecycle cutoff.

    Monetary segments reuse the already-approved overtime calculation. No BASE_LEASE
    proration or new monetary formula is introduced here. A split is materializable
    only when independently calculated segments conserve the original immutable
    financial effect exactly; otherwise the operation fails closed.
    """

    if effect.item_type is not FinancialEffectType.OVERTIME:
        raise FixedCutoffSplitError("only OVERTIME supports temporal split allocation")

    start = effect.billing_period_start
    end = effect.billing_period_end
    if start is None or end is None or start.tzinfo is None or end.tzinfo is None:
        raise FixedCutoffSplitError(
            "OVERTIME split requires timezone-aware temporal financial evidence"
        )
    if start >= end:
        raise FixedCutoffSplitError("OVERTIME temporal financial interval is invalid")

    start_cycle = _cycle_for(context, start)
    end_cycle = _cycle_for(context, end - timedelta(microseconds=1))

    if start_cycle == end_cycle:
        segment = _segment_overtime(context, effect, start=start, end=end)
        if segment is None:
            raise FixedCutoffSplitError("OVERTIME segment has no completed minute")
        if segment.total_amount != effect.total_amount or segment.quantity != effect.quantity:
            raise FixedCutoffSplitError(
                "OVERTIME segment does not preserve immutable financial evidence"
            )
        return (AllocatedFinancialEffect(cycle=start_cycle, effect=segment),)

    cutoff = start_cycle.end
    if end > end_cycle.end or end_cycle.start != cutoff:
        raise FixedCutoffSplitError(
            "OVERTIME financial effect crosses more than one Billing cutoff"
        )
    if not start < cutoff < end:
        raise FixedCutoffSplitError("OVERTIME cutoff allocation is ambiguous")

    pre = _segment_overtime(context, effect, start=start, end=cutoff)
    post = _segment_overtime(context, effect, start=cutoff, end=end)
    if pre is None or post is None:
        raise FixedCutoffSplitError(
            "OVERTIME cutoff split cannot produce two materializable segments"
        )

    split_quantity = pre.quantity + post.quantity
    split_total = quantize_money(pre.total_amount + post.total_amount)
    if split_quantity != effect.quantity or split_total != effect.total_amount:
        raise FixedCutoffSplitError(
            "OVERTIME cutoff split does not preserve immutable financial evidence"
        )

    return (
        AllocatedFinancialEffect(cycle=start_cycle, effect=pre),
        AllocatedFinancialEffect(cycle=end_cycle, effect=post),
    )
