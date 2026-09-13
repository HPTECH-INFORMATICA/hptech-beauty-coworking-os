from __future__ import annotations

from datetime import UTC, date, datetime, time
from uuid import UUID

import pytest

from bcos_worker.billing_cycle import (
    BillingCycleResolutionError,
    resolve_billing_cycle,
)
from bcos_worker.professional_billing_contract import ProfessionalBillingContract

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
PROFESSIONAL_ID = UUID("00000000-0000-0000-0000-000000000002")
CONTRACT_ID = UUID("00000000-0000-0000-0000-000000000003")


def _contract(
    *,
    lifecycle_mode: str,
    weekday: int | None = None,
    anchor: date | None = None,
    month_day: int | None = None,
    closing_time: time | None = time(18, 0),
) -> ProfessionalBillingContract:
    return ProfessionalBillingContract(
        id=CONTRACT_ID,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        invoice_mode="ACCUMULATED_OPEN_INVOICE",
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        valid_until=None,
        lifecycle_mode=lifecycle_mode,
        lifecycle_weekday=weekday,
        lifecycle_biweekly_anchor=anchor,
        lifecycle_month_day=month_day,
        lifecycle_closing_time=closing_time,
        cycle_allocation_policy="USAGE_COMPLETION",
    )


def test_resolves_weekly_cycle_in_unit_timezone() -> None:
    cycle = resolve_billing_cycle(
        contract=_contract(lifecycle_mode="WEEKLY", weekday=4),
        unit_timezone="America/Sao_Paulo",
        reference_instant=datetime(2026, 9, 13, 15, 0, tzinfo=UTC),
    )

    assert cycle is not None
    assert cycle.start == datetime(2026, 9, 11, 21, 0, tzinfo=UTC)
    assert cycle.end == datetime(2026, 9, 18, 21, 0, tzinfo=UTC)


def test_exact_weekly_cutoff_begins_new_cycle() -> None:
    cycle = resolve_billing_cycle(
        contract=_contract(lifecycle_mode="WEEKLY", weekday=4),
        unit_timezone="America/Sao_Paulo",
        reference_instant=datetime(2026, 9, 11, 21, 0, tzinfo=UTC),
    )

    assert cycle is not None
    assert cycle.start == datetime(2026, 9, 11, 21, 0, tzinfo=UTC)


def test_resolves_biweekly_cycle_from_anchor() -> None:
    cycle = resolve_billing_cycle(
        contract=_contract(
            lifecycle_mode="BIWEEKLY",
            anchor=date(2026, 9, 4),
        ),
        unit_timezone="America/Sao_Paulo",
        reference_instant=datetime(2026, 9, 13, 15, 0, tzinfo=UTC),
    )

    assert cycle is not None
    assert cycle.start == datetime(2026, 9, 4, 21, 0, tzinfo=UTC)
    assert cycle.end == datetime(2026, 9, 18, 21, 0, tzinfo=UTC)


def test_monthly_day_overflow_uses_last_calendar_day() -> None:
    cycle = resolve_billing_cycle(
        contract=_contract(lifecycle_mode="MONTHLY", month_day=31),
        unit_timezone="America/Sao_Paulo",
        reference_instant=datetime(2026, 3, 1, 12, 0, tzinfo=UTC),
    )

    assert cycle is not None
    assert cycle.start == datetime(2026, 2, 28, 21, 0, tzinfo=UTC)
    assert cycle.end == datetime(2026, 3, 31, 21, 0, tzinfo=UTC)


def test_manual_cycle_has_no_automatic_boundaries() -> None:
    cycle = resolve_billing_cycle(
        contract=_contract(
            lifecycle_mode="MANUAL",
            closing_time=None,
        ),
        unit_timezone="America/Sao_Paulo",
        reference_instant=datetime(2026, 9, 13, 15, 0, tzinfo=UTC),
    )

    assert cycle is None


def test_rejects_invalid_timezone() -> None:
    with pytest.raises(
        BillingCycleResolutionError,
        match="valid IANA timezone",
    ):
        resolve_billing_cycle(
            contract=_contract(lifecycle_mode="WEEKLY", weekday=4),
            unit_timezone="Invalid/Timezone",
            reference_instant=datetime(2026, 9, 13, 15, 0, tzinfo=UTC),
        )


def test_rejects_naive_reference_instant() -> None:
    with pytest.raises(
        BillingCycleResolutionError,
        match="timezone-aware",
    ):
        resolve_billing_cycle(
            contract=_contract(lifecycle_mode="WEEKLY", weekday=4),
            unit_timezone="America/Sao_Paulo",
            reference_instant=datetime(2026, 9, 13, 15, 0),
        )
