from __future__ import annotations

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

import pytest

from bcos_worker.overtime import (
    OvertimeClassification,
    OvertimeTemporalError,
    classify_overtime,
)

ZONE = ZoneInfo("America/Sao_Paulo")


def utc_dt(hour: int, minute: int, second: int = 0) -> datetime:
    return datetime(2026, 9, 7, hour, minute, second, tzinfo=UTC)


def local_dt(hour: int, minute: int, second: int = 0) -> datetime:
    return datetime(2026, 9, 7, hour, minute, second, tzinfo=ZONE)


def test_no_overtime_when_checkout_is_at_booking_end() -> None:
    result = classify_overtime(
        booking_ends_at=utc_dt(16, 0),
        checked_out_at=utc_dt(16, 0),
        local_checked_out_at=local_dt(13, 0),
        reception_closes_at=time(18, 0),
        reception_is_closed=False,
    )

    assert result.classification is OvertimeClassification.NONE
    assert result.actual_overtime_seconds == 0
    assert result.billable_overtime_minutes == 0


def test_less_than_one_complete_minute_is_not_billable() -> None:
    result = classify_overtime(
        booking_ends_at=utc_dt(16, 0),
        checked_out_at=utc_dt(16, 0, 59),
        local_checked_out_at=local_dt(13, 0, 59),
        reception_closes_at=time(18, 0),
        reception_is_closed=False,
    )

    assert result.classification is OvertimeClassification.NONE
    assert result.actual_overtime_seconds == 59
    assert result.billable_overtime_minutes == 0


@pytest.mark.parametrize(
    ("minutes", "seconds"),
    [
        (1, 0),
        (1, 59),
        (29, 0),
        (29, 59),
    ],
)
def test_one_through_twenty_nine_complete_minutes_are_proportional(
    minutes: int,
    seconds: int,
) -> None:
    result = classify_overtime(
        booking_ends_at=utc_dt(16, 0),
        checked_out_at=utc_dt(16, minutes, seconds),
        local_checked_out_at=local_dt(13, minutes, seconds),
        reception_closes_at=time(18, 0),
        reception_is_closed=False,
    )

    assert result.classification is OvertimeClassification.PROPORTIONAL
    assert result.billable_overtime_minutes == minutes


@pytest.mark.parametrize(
    ("minute", "second", "expected_minutes"),
    [
        (30, 0, 30),
        (30, 59, 30),
        (31, 0, 31),
    ],
)
def test_thirty_complete_minutes_or_more_reaches_full_hour_threshold(
    minute: int,
    second: int,
    expected_minutes: int,
) -> None:
    result = classify_overtime(
        booking_ends_at=utc_dt(16, 0),
        checked_out_at=utc_dt(16, minute, second),
        local_checked_out_at=local_dt(13, minute, second),
        reception_closes_at=time(18, 0),
        reception_is_closed=False,
    )

    assert result.classification is OvertimeClassification.FULL_HOUR
    assert result.billable_overtime_minutes == expected_minutes


def test_closed_reception_day_excludes_overtime() -> None:
    result = classify_overtime(
        booking_ends_at=utc_dt(16, 0),
        checked_out_at=utc_dt(16, 20),
        local_checked_out_at=local_dt(13, 20),
        reception_closes_at=None,
        reception_is_closed=True,
    )

    assert (
        result.classification
        is OvertimeClassification.EXCLUDED_AFTER_RECEPTION_CLOSE
    )
    assert result.billable_overtime_minutes == 0


def test_checkout_exactly_at_reception_close_is_not_excluded() -> None:
    result = classify_overtime(
        booking_ends_at=utc_dt(20, 30),
        checked_out_at=utc_dt(21, 0),
        local_checked_out_at=local_dt(18, 0),
        reception_closes_at=time(18, 0),
        reception_is_closed=False,
    )

    assert result.classification is OvertimeClassification.FULL_HOUR
    assert result.billable_overtime_minutes == 30


def test_checkout_after_reception_close_is_excluded() -> None:
    result = classify_overtime(
        booking_ends_at=utc_dt(20, 30),
        checked_out_at=utc_dt(21, 0, 1),
        local_checked_out_at=local_dt(18, 0, 1),
        reception_closes_at=time(18, 0),
        reception_is_closed=False,
    )

    assert (
        result.classification
        is OvertimeClassification.EXCLUDED_AFTER_RECEPTION_CLOSE
    )
    assert result.billable_overtime_minutes == 0


def test_open_reception_day_without_close_time_fails_closed() -> None:
    with pytest.raises(
        OvertimeTemporalError,
        match="open reception day must define reception_closes_at",
    ):
        classify_overtime(
            booking_ends_at=utc_dt(16, 0),
            checked_out_at=utc_dt(16, 20),
            local_checked_out_at=local_dt(13, 20),
            reception_closes_at=None,
            reception_is_closed=False,
        )
