"""Tests for BCOS finite booking-series domain rules."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from bcos_api.bookings.series_domain import (
    InvalidBookingSeries,
    expand_booking_occurrences,
    validate_physical_periods_do_not_overlap,
)

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def _start() -> datetime:
    return datetime(2026, 9, 7, 9, 0, tzinfo=SAO_PAULO)


def test_expand_count_rrule_materializes_all_occurrences() -> None:
    occurrences = expand_booking_occurrences(
        starts_at=_start(),
        duration_minutes=60,
        rrule="FREQ=DAILY;COUNT=3",
        timezone="America/Sao_Paulo",
    )

    assert len(occurrences) == 3
    assert occurrences[0].starts_at == _start()
    assert occurrences[0].ends_at == _start() + timedelta(hours=1)
    assert occurrences[1].starts_at == _start() + timedelta(days=1)
    assert occurrences[2].starts_at == _start() + timedelta(days=2)


def test_expand_until_rrule_is_finite() -> None:
    occurrences = expand_booking_occurrences(
        starts_at=_start(),
        duration_minutes=30,
        rrule="FREQ=DAILY;UNTIL=20260909T120000Z",
        timezone="America/Sao_Paulo",
    )

    assert len(occurrences) == 3
    assert occurrences[-1].starts_at.date().isoformat() == "2026-09-09"


def test_rrule_prefix_is_accepted() -> None:
    occurrences = expand_booking_occurrences(
        starts_at=_start(),
        duration_minutes=60,
        rrule="RRULE:FREQ=DAILY;COUNT=2",
        timezone="America/Sao_Paulo",
    )

    assert len(occurrences) == 2


def test_unbounded_rrule_is_rejected() -> None:
    with pytest.raises(
        InvalidBookingSeries,
        match="finite using COUNT or UNTIL",
    ):
        expand_booking_occurrences(
            starts_at=_start(),
            duration_minutes=60,
            rrule="FREQ=DAILY",
            timezone="America/Sao_Paulo",
        )


def test_rrule_with_count_and_until_is_rejected() -> None:
    with pytest.raises(
        InvalidBookingSeries,
        match="must not define both COUNT and UNTIL",
    ):
        expand_booking_occurrences(
            starts_at=_start(),
            duration_minutes=60,
            rrule="FREQ=DAILY;COUNT=2;UNTIL=20260909T120000Z",
            timezone="America/Sao_Paulo",
        )


def test_multiline_rrule_is_rejected() -> None:
    with pytest.raises(
        InvalidBookingSeries,
        match="exactly one recurrence rule",
    ):
        expand_booking_occurrences(
            starts_at=_start(),
            duration_minutes=60,
            rrule="DTSTART:20260907T120000Z\nRRULE:FREQ=DAILY;COUNT=2",
            timezone="America/Sao_Paulo",
        )


def test_duplicate_rrule_property_is_rejected() -> None:
    with pytest.raises(
        InvalidBookingSeries,
        match="must not repeat properties",
    ):
        expand_booking_occurrences(
            starts_at=_start(),
            duration_minutes=60,
            rrule="FREQ=DAILY;COUNT=2;COUNT=3",
            timezone="America/Sao_Paulo",
        )


@pytest.mark.parametrize(
    "rrule",
    [
        "",
        "   ",
    ],
)
def test_blank_rrule_is_rejected(rrule: str) -> None:
    with pytest.raises(InvalidBookingSeries, match="must not be blank"):
        expand_booking_occurrences(
            starts_at=_start(),
            duration_minutes=60,
            rrule=rrule,
            timezone="America/Sao_Paulo",
        )


def test_invalid_timezone_is_rejected() -> None:
    with pytest.raises(
        InvalidBookingSeries,
        match="valid IANA timezone",
    ):
        expand_booking_occurrences(
            starts_at=_start(),
            duration_minutes=60,
            rrule="FREQ=DAILY;COUNT=2",
            timezone="Invalid/Timezone",
        )


def test_blank_timezone_is_rejected() -> None:
    with pytest.raises(
        InvalidBookingSeries,
        match="timezone must not be blank",
    ):
        expand_booking_occurrences(
            starts_at=_start(),
            duration_minutes=60,
            rrule="FREQ=DAILY;COUNT=2",
            timezone="   ",
        )


def test_naive_starts_at_is_rejected() -> None:
    with pytest.raises(
        InvalidBookingSeries,
        match="starts_at must be timezone-aware",
    ):
        expand_booking_occurrences(
            starts_at=datetime(2026, 9, 7, 9, 0),
            duration_minutes=60,
            rrule="FREQ=DAILY;COUNT=2",
            timezone="America/Sao_Paulo",
        )


@pytest.mark.parametrize("duration_minutes", [0, -1])
def test_non_positive_duration_is_rejected(
    duration_minutes: int,
) -> None:
    with pytest.raises(
        InvalidBookingSeries,
        match="duration_minutes must be at least 1",
    ):
        expand_booking_occurrences(
            starts_at=_start(),
            duration_minutes=duration_minutes,
            rrule="FREQ=DAILY;COUNT=2",
            timezone="America/Sao_Paulo",
        )


def test_business_occurrences_may_be_adjacent() -> None:
    occurrences = expand_booking_occurrences(
        starts_at=_start(),
        duration_minutes=60,
        rrule="FREQ=HOURLY;COUNT=3",
        timezone="America/Sao_Paulo",
    )

    assert len(occurrences) == 3
    assert occurrences[0].ends_at == occurrences[1].starts_at
    assert occurrences[1].ends_at == occurrences[2].starts_at


def test_overlapping_business_occurrences_are_rejected() -> None:
    with pytest.raises(
        InvalidBookingSeries,
        match="overlapping booking occurrences",
    ):
        expand_booking_occurrences(
            starts_at=_start(),
            duration_minutes=61,
            rrule="FREQ=HOURLY;COUNT=2",
            timezone="America/Sao_Paulo",
        )


def test_adjacent_physical_periods_do_not_overlap() -> None:
    start = _start()

    validate_physical_periods_do_not_overlap(
        [
            (start, start + timedelta(hours=1)),
            (start + timedelta(hours=1), start + timedelta(hours=2)),
        ]
    )


def test_buffer_induced_physical_overlap_is_rejected() -> None:
    start = _start()

    with pytest.raises(
        InvalidBookingSeries,
        match="overlap after resource buffers",
    ):
        validate_physical_periods_do_not_overlap(
            [
                (
                    start - timedelta(minutes=10),
                    start + timedelta(hours=1, minutes=10),
                ),
                (
                    start + timedelta(minutes=50),
                    start + timedelta(hours=2, minutes=10),
                ),
            ]
        )


def test_count_zero_is_rejected_because_it_produces_no_occurrences() -> None:
    with pytest.raises(
        InvalidBookingSeries,
        match="at least one occurrence",
    ):
        expand_booking_occurrences(
            starts_at=_start(),
            duration_minutes=60,
            rrule="FREQ=DAILY;COUNT=0",
            timezone="America/Sao_Paulo",
        )
