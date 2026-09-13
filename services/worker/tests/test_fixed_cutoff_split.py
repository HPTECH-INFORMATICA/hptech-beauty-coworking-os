from datetime import UTC, datetime, time
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from bcos_worker.financial_effects import calculate_usage_financial_effects
from bcos_worker.fixed_cutoff_split import (
    FixedCutoffSplitError,
    allocate_fixed_cutoff_overtime,
)
from bcos_worker.pricing_context import ReceptionHours, UsagePricingContext
from bcos_worker.pricing_rule import OvertimeRule, PricingModality, PricingRuleDefinitionV1
from bcos_worker.professional_billing_contract import ProfessionalBillingContract

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
USAGE_ID = UUID("00000000-0000-0000-0000-000000000002")
BOOKING_ID = UUID("00000000-0000-0000-0000-000000000003")
RESOURCE_ID = UUID("00000000-0000-0000-0000-000000000004")
PROFESSIONAL_ID = UUID("00000000-0000-0000-0000-000000000005")
UNIT_ID = UUID("00000000-0000-0000-0000-000000000006")
CONTRACT_ID = UUID("00000000-0000-0000-0000-000000000007")


def _context(*, lifecycle_closing_time: time) -> UsagePricingContext:
    zone = ZoneInfo("America/Sao_Paulo")
    booking_starts_at = datetime(2026, 9, 11, 19, 30, tzinfo=UTC)
    booking_ends_at = datetime(2026, 9, 11, 20, 30, tzinfo=UTC)
    checked_out_at = datetime(2026, 9, 11, 21, 20, tzinfo=UTC)

    pricing_rule = PricingRuleDefinitionV1(
        schema_version=1,
        modality=PricingModality.HOURLY,
        base_price_amount=Decimal("100.00"),
        overtime=OvertimeRule(
            hourly_price_amount=Decimal("60.00"),
            proportional_until_minutes=29,
            full_hour_from_minutes=30,
            forgiveness_allowed=True,
        ),
        conflict_penalty=None,
    )
    contract = ProfessionalBillingContract(
        id=CONTRACT_ID,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        invoice_mode="ACCUMULATED_OPEN_INVOICE",
        valid_from=datetime(2026, 9, 1, tzinfo=UTC),
        valid_until=None,
        lifecycle_mode="WEEKLY",
        lifecycle_weekday=4,
        lifecycle_biweekly_anchor=None,
        lifecycle_month_day=None,
        lifecycle_closing_time=lifecycle_closing_time,
        cycle_allocation_policy="FIXED_CUTOFF_SPLIT",
    )

    return UsagePricingContext(
        tenant_id=TENANT_ID,
        usage_id=USAGE_ID,
        booking_id=BOOKING_ID,
        resource_id=RESOURCE_ID,
        professional_id=PROFESSIONAL_ID,
        unit_id=UNIT_ID,
        usage_status="COMPLETED",
        checked_in_at=booking_starts_at,
        checked_out_at=checked_out_at,
        booking_starts_at=booking_starts_at,
        booking_ends_at=booking_ends_at,
        pricing_snapshot={},
        pricing_rule=pricing_rule,
        professional_billing_contract=contract,
        unit_timezone="America/Sao_Paulo",
        local_checked_out_at=checked_out_at.astimezone(zone),
        reception_hours=ReceptionHours(
            day_of_week=4,
            opens_at=time(8, 0),
            closes_at=time(18, 0),
            is_closed=False,
        ),
    )


def test_fixed_cutoff_split_produces_two_deterministic_overtime_segments() -> None:
    context = _context(lifecycle_closing_time=time(17, 45))
    overtime = calculate_usage_financial_effects(context).overtime[0]

    allocated = allocate_fixed_cutoff_overtime(context, overtime)

    assert len(allocated) == 2

    pre, post = allocated
    cutoff = datetime(2026, 9, 11, 20, 45, tzinfo=UTC)

    assert pre.effect.billing_period_start == datetime(2026, 9, 11, 20, 30, tzinfo=UTC)
    assert pre.effect.billing_period_end == cutoff
    assert pre.effect.quantity == Decimal("15")
    assert pre.effect.total_amount == Decimal("15.00")
    assert pre.cycle.end == cutoff

    assert post.effect.billing_period_start == cutoff
    assert post.effect.billing_period_end == datetime(2026, 9, 11, 21, 0, tzinfo=UTC)
    assert post.effect.quantity == Decimal("15")
    assert post.effect.total_amount == Decimal("15.00")
    assert post.cycle.start == cutoff


def test_fixed_cutoff_split_fails_closed_when_a_segment_has_no_completed_minute() -> None:
    context = _context(lifecycle_closing_time=time(17, 30, 30))
    overtime = calculate_usage_financial_effects(context).overtime[0]

    with pytest.raises(
        FixedCutoffSplitError,
        match="cannot produce two materializable segments",
    ):
        allocate_fixed_cutoff_overtime(context, overtime)
