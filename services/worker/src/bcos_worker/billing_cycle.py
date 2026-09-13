"""Deterministic accumulated Billing-cycle resolution for BCOS."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bcos_worker.professional_billing_contract import ProfessionalBillingContract


class BillingCycleResolutionError(RuntimeError):
    """Raised when an accumulated Billing cycle cannot be resolved safely."""


@dataclass(frozen=True, slots=True)
class BillingCycle:
    start: datetime
    end: datetime


def _zone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        raise BillingCycleResolutionError(
            "unit timezone must be a valid IANA timezone"
        ) from None


def _strict_local_datetime(
    *,
    local_date: date,
    local_time: time,
    zone: ZoneInfo,
) -> datetime:
    naive = datetime.combine(local_date, local_time)
    first = naive.replace(tzinfo=zone, fold=0)
    second = naive.replace(tzinfo=zone, fold=1)

    first_roundtrip = first.astimezone(UTC).astimezone(zone).replace(tzinfo=None)
    second_roundtrip = second.astimezone(UTC).astimezone(zone).replace(tzinfo=None)

    valid_first = first_roundtrip == naive
    valid_second = second_roundtrip == naive

    if not valid_first and not valid_second:
        raise BillingCycleResolutionError(
            "Billing lifecycle cutoff falls in a nonexistent local time"
        )

    if valid_first and valid_second and first.utcoffset() != second.utcoffset():
        raise BillingCycleResolutionError(
            "Billing lifecycle cutoff falls in an ambiguous local time"
        )

    return first if valid_first else second


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise BillingCycleResolutionError(
            "Billing cycle reference instant must be timezone-aware"
        )
    return value.astimezone(UTC)


def _validate_cycle(start: datetime, end: datetime) -> BillingCycle:
    start_utc = _as_utc(start)
    end_utc = _as_utc(end)
    if start_utc >= end_utc:
        raise BillingCycleResolutionError("invalid Billing cycle interval")
    return BillingCycle(start=start_utc, end=end_utc)


def _weekly_cycle(
    *,
    reference: datetime,
    weekday: int,
    closing_time: time,
    zone: ZoneInfo,
) -> BillingCycle:
    local_reference = reference.astimezone(zone)
    days_since_cutoff_weekday = (local_reference.weekday() - weekday) % 7
    previous_date = local_reference.date() - timedelta(days=days_since_cutoff_weekday)
    previous_cutoff = _strict_local_datetime(
        local_date=previous_date,
        local_time=closing_time,
        zone=zone,
    )

    if local_reference < previous_cutoff:
        previous_date -= timedelta(days=7)
        previous_cutoff = _strict_local_datetime(
            local_date=previous_date,
            local_time=closing_time,
            zone=zone,
        )

    next_cutoff = _strict_local_datetime(
        local_date=previous_date + timedelta(days=7),
        local_time=closing_time,
        zone=zone,
    )
    return _validate_cycle(previous_cutoff, next_cutoff)


def _biweekly_cycle(
    *,
    reference: datetime,
    anchor: date,
    closing_time: time,
    zone: ZoneInfo,
) -> BillingCycle:
    local_reference = reference.astimezone(zone)
    anchor_cutoff = _strict_local_datetime(
        local_date=anchor,
        local_time=closing_time,
        zone=zone,
    )

    delta_days = (local_reference.date() - anchor).days
    cycle_index = delta_days // 14
    previous_date = anchor + timedelta(days=cycle_index * 14)
    previous_cutoff = _strict_local_datetime(
        local_date=previous_date,
        local_time=closing_time,
        zone=zone,
    )

    if local_reference < previous_cutoff:
        previous_date -= timedelta(days=14)
        previous_cutoff = _strict_local_datetime(
            local_date=previous_date,
            local_time=closing_time,
            zone=zone,
        )

    if local_reference >= anchor_cutoff and previous_date < anchor:
        raise BillingCycleResolutionError("invalid BIWEEKLY cycle resolution")

    next_cutoff = _strict_local_datetime(
        local_date=previous_date + timedelta(days=14),
        local_time=closing_time,
        zone=zone,
    )
    return _validate_cycle(previous_cutoff, next_cutoff)


def _month_cutoff_date(year: int, month: int, month_day: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(month_day, last_day))


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _monthly_cycle(
    *,
    reference: datetime,
    month_day: int,
    closing_time: time,
    zone: ZoneInfo,
) -> BillingCycle:
    local_reference = reference.astimezone(zone)
    current_date = _month_cutoff_date(
        local_reference.year,
        local_reference.month,
        month_day,
    )
    current_cutoff = _strict_local_datetime(
        local_date=current_date,
        local_time=closing_time,
        zone=zone,
    )

    if local_reference >= current_cutoff:
        previous_cutoff = current_cutoff
        next_year, next_month = _next_month(
            local_reference.year,
            local_reference.month,
        )
        next_cutoff = _strict_local_datetime(
            local_date=_month_cutoff_date(next_year, next_month, month_day),
            local_time=closing_time,
            zone=zone,
        )
    else:
        previous_year, previous_month = _previous_month(
            local_reference.year,
            local_reference.month,
        )
        previous_cutoff = _strict_local_datetime(
            local_date=_month_cutoff_date(
                previous_year,
                previous_month,
                month_day,
            ),
            local_time=closing_time,
            zone=zone,
        )
        next_cutoff = current_cutoff

    return _validate_cycle(previous_cutoff, next_cutoff)


def resolve_billing_cycle(
    *,
    contract: ProfessionalBillingContract,
    unit_timezone: str,
    reference_instant: datetime,
) -> BillingCycle | None:
    """Resolve the accumulated Invoice cycle containing ``reference_instant``.

    ``None`` is the canonical MANUAL lifecycle identity: no automatic boundaries.
    """

    if contract.invoice_mode != "ACCUMULATED_OPEN_INVOICE":
        raise BillingCycleResolutionError(
            "accumulated Billing cycle requires ACCUMULATED_OPEN_INVOICE"
        )

    if reference_instant.tzinfo is None:
        raise BillingCycleResolutionError(
            "Billing cycle reference instant must be timezone-aware"
        )

    lifecycle_mode = contract.lifecycle_mode
    zone = _zone(unit_timezone)

    if lifecycle_mode == "MANUAL":
        if any(
            value is not None
            for value in (
                contract.lifecycle_weekday,
                contract.lifecycle_biweekly_anchor,
                contract.lifecycle_month_day,
                contract.lifecycle_closing_time,
            )
        ):
            raise BillingCycleResolutionError(
                "MANUAL Billing lifecycle cannot define automatic cutoff fields"
            )
        return None

    closing_time = contract.lifecycle_closing_time
    if closing_time is None:
        raise BillingCycleResolutionError(
            "automatic Billing lifecycle requires lifecycle_closing_time"
        )

    if lifecycle_mode == "WEEKLY":
        weekday = contract.lifecycle_weekday
        if weekday is None or not 0 <= weekday <= 6:
            raise BillingCycleResolutionError(
                "WEEKLY Billing lifecycle requires a valid lifecycle_weekday"
            )
        return _weekly_cycle(
            reference=reference_instant,
            weekday=weekday,
            closing_time=closing_time,
            zone=zone,
        )

    if lifecycle_mode == "BIWEEKLY":
        anchor = contract.lifecycle_biweekly_anchor
        if anchor is None:
            raise BillingCycleResolutionError(
                "BIWEEKLY Billing lifecycle requires lifecycle_biweekly_anchor"
            )
        return _biweekly_cycle(
            reference=reference_instant,
            anchor=anchor,
            closing_time=closing_time,
            zone=zone,
        )

    if lifecycle_mode == "MONTHLY":
        month_day = contract.lifecycle_month_day
        if month_day is None or not 1 <= month_day <= 31:
            raise BillingCycleResolutionError(
                "MONTHLY Billing lifecycle requires a valid lifecycle_month_day"
            )
        return _monthly_cycle(
            reference=reference_instant,
            month_day=month_day,
            closing_time=closing_time,
            zone=zone,
        )

    raise BillingCycleResolutionError(
        "unsupported accumulated Billing lifecycle mode"
    )
