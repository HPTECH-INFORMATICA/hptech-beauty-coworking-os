"""Deterministic financial effects for a completed BCOS Usage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from bcos_worker.overtime import classify_overtime
from bcos_worker.overtime_money import calculate_overtime_amount, quantize_money
from bcos_worker.pricing_context import UsagePricingContext


class FinancialEffectType(StrEnum):
    BASE_LEASE = "BASE_LEASE"
    OVERTIME = "OVERTIME"


@dataclass(frozen=True, slots=True)
class FinancialEffect:
    item_type: FinancialEffectType
    description: str
    quantity: Decimal
    unit_amount: Decimal
    total_amount: Decimal
    reception_segment: str | None = None
    billing_period_start: datetime | None = None
    billing_period_end: datetime | None = None


@dataclass(frozen=True, slots=True)
class UsageFinancialEffects:
    base_lease: FinancialEffect
    overtime: tuple[FinancialEffect, ...]


def calculate_usage_financial_effects(
    context: UsagePricingContext,
) -> UsageFinancialEffects:
    """Calculate materializable Usage financial facts without database writes."""

    rule = context.pricing_rule

    base_amount = quantize_money(rule.base_price_amount)

    base_lease = FinancialEffect(
        item_type=FinancialEffectType.BASE_LEASE,
        description="Base lease",
        quantity=Decimal("1"),
        unit_amount=base_amount,
        total_amount=base_amount,
    )

    temporal = classify_overtime(
        booking_ends_at=context.booking_ends_at,
        checked_out_at=context.checked_out_at,
        local_checked_out_at=context.local_checked_out_at,
        reception_closes_at=context.reception_hours.closes_at,
        reception_is_closed=context.reception_hours.is_closed,
        proportional_until_minutes=rule.overtime.proportional_until_minutes,
        full_hour_from_minutes=rule.overtime.full_hour_from_minutes,
    )

    overtime_effects: list[FinancialEffect] = []

    # M7-A2-T1 freezes reception closing as the maximum chargeable instant.
    # Overtime after reception close remains temporally classified for auditability,
    # but it must never materialize a financial OVERTIME effect.
    segment = temporal.before_reception_close
    if segment.completed_minutes > 0:
        closes_at = context.reception_hours.closes_at
        if closes_at is None:
            raise RuntimeError(
                "chargeable overtime requires reception closing evidence"
            )

        local_close = datetime.combine(
            context.local_checked_out_at.date(),
            closes_at,
            tzinfo=context.local_checked_out_at.tzinfo,
        )
        chargeable_end = min(context.local_checked_out_at, local_close).astimezone(UTC)
        chargeable_start = context.booking_ends_at.astimezone(UTC)

        if chargeable_start >= chargeable_end:
            raise RuntimeError("chargeable overtime interval is invalid")

        money = calculate_overtime_amount(
            hourly_price_amount=rule.overtime.hourly_price_amount,
            completed_minutes=segment.completed_minutes,
            proportional_until_minutes=rule.overtime.proportional_until_minutes,
            full_hour_from_minutes=rule.overtime.full_hour_from_minutes,
        )

        overtime_effects.append(
            FinancialEffect(
                item_type=FinancialEffectType.OVERTIME,
                description="Overtime",
                quantity=Decimal(segment.completed_minutes),
                unit_amount=quantize_money(rule.overtime.hourly_price_amount),
                total_amount=money.amount,
                reception_segment="BEFORE_RECEPTION_CLOSE",
                billing_period_start=chargeable_start,
                billing_period_end=chargeable_end,
            )
        )

    return UsageFinancialEffects(
        base_lease=base_lease,
        overtime=tuple(overtime_effects),
    )
