from datetime import UTC, datetime, time
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from bcos_worker.financial_effects import (
    FinancialEffectType,
    calculate_usage_financial_effects,
)
from bcos_worker.pricing_context import ReceptionHours, UsagePricingContext
from bcos_worker.pricing_rule import (
    OvertimeRule,
    PricingModality,
    PricingRuleDefinitionV1,
)
from bcos_worker.professional_billing_contract import ProfessionalBillingContract

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
USAGE_ID = UUID("00000000-0000-0000-0000-000000000002")
BOOKING_ID = UUID("00000000-0000-0000-0000-000000000003")
RESOURCE_ID = UUID("00000000-0000-0000-0000-000000000004")
PROFESSIONAL_ID = UUID("00000000-0000-0000-0000-000000000005")
UNIT_ID = UUID("00000000-0000-0000-0000-000000000006")
CONTRACT_ID = UUID("00000000-0000-0000-0000-000000000007")


def _context(
    *,
    checked_out_at: datetime,
    reception_closes_at: time | None = time(18, 0),
    reception_is_closed: bool = False,
) -> UsagePricingContext:
    zone = ZoneInfo("America/Sao_Paulo")

    booking_starts_at = datetime(2026, 9, 11, 19, 30, tzinfo=UTC)
    booking_ends_at = datetime(2026, 9, 11, 20, 30, tzinfo=UTC)

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
        invoice_mode="PER_USAGE",
        valid_from=datetime(2026, 9, 1, tzinfo=UTC),
        valid_until=None,
        lifecycle_mode=None,
        lifecycle_weekday=None,
        lifecycle_biweekly_anchor=None,
        lifecycle_month_day=None,
        lifecycle_closing_time=None,
        cycle_allocation_policy=None,
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
            closes_at=reception_closes_at,
            is_closed=reception_is_closed,
        ),
    )


def test_materializes_base_lease_without_overtime() -> None:
    context = _context(
        checked_out_at=datetime(2026, 9, 11, 20, 30, tzinfo=UTC),
    )

    result = calculate_usage_financial_effects(context)

    assert result.base_lease.item_type is FinancialEffectType.BASE_LEASE
    assert result.base_lease.quantity == Decimal("1")
    assert result.base_lease.unit_amount == Decimal("100.00")
    assert result.base_lease.total_amount == Decimal("100.00")
    assert result.overtime == ()


def test_only_overtime_before_reception_close_is_chargeable() -> None:
    context = _context(
        checked_out_at=datetime(2026, 9, 11, 21, 20, tzinfo=UTC),
    )

    result = calculate_usage_financial_effects(context)

    assert len(result.overtime) == 1

    overtime = result.overtime[0]

    assert overtime.item_type is FinancialEffectType.OVERTIME
    assert overtime.reception_segment == "BEFORE_RECEPTION_CLOSE"
    assert overtime.quantity == Decimal("30")
    assert overtime.unit_amount == Decimal("60.00")
    assert overtime.total_amount == Decimal("60.00")


def test_closed_reception_day_never_generates_overtime_charge() -> None:
    context = _context(
        checked_out_at=datetime(2026, 9, 11, 20, 50, tzinfo=UTC),
        reception_closes_at=None,
        reception_is_closed=True,
    )

    result = calculate_usage_financial_effects(context)

    assert result.overtime == ()
