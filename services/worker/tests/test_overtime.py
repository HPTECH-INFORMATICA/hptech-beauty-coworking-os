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

    assert result.actual_overtime_seconds == 0
    assert result.completed_overtime_minutes == 0

    assert result.before_reception_close.classification is OvertimeClassification.NONE
    assert result.before_reception_close.actual_seconds == 0
    assert result.before_reception_close.completed_minutes == 0

    assert result.after_reception_close.classification is OvertimeClassification.NONE
    assert result.after_reception_close.actual_seconds == 0
    assert result.after_reception_close.completed_minutes == 0


def test_less_than_one_complete_minute_is_accounted_but_not_promoted() -> None:
    result = classify_overtime(
        booking_ends_at=utc_dt(16, 0),
        checked_out_at=utc_dt(16, 0, 59),
        local_checked_out_at=local_dt(13, 0, 59),
        reception_closes_at=time(18, 0),
        reception_is_closed=False,
    )

    assert result.actual_overtime_seconds == 59
    assert result.completed_overtime_minutes == 0
    assert result.before_reception_close.actual_seconds == 59
    assert result.before_reception_close.completed_minutes == 0
    assert result.before_reception_close.classification is OvertimeClassification.NONE
    assert result.after_reception_close.actual_seconds == 0


@pytest.mark.parametrize(
    ("minutes", "seconds"),
    [
        (1, 0),
        (1, 59),
        (29, 0),
        (29, 59),
    ],
)
def test_one_through_twenty_nine_complete_minutes_before_close_are_proportional(
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

    assert result.completed_overtime_minutes == minutes
    assert result.before_reception_close.completed_minutes == minutes
    assert (
        result.before_reception_close.classification
        is OvertimeClassification.PROPORTIONAL
    )
    assert result.after_reception_close.completed_minutes == 0


@pytest.mark.parametrize(
    ("minute", "second", "expected_minutes"),
    [
        (30, 0, 30),
        (30, 59, 30),
        (31, 0, 31),
    ],
)
def test_thirty_complete_minutes_or_more_before_close_reaches_full_hour_threshold(
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

    assert result.completed_overtime_minutes == expected_minutes
    assert result.before_reception_close.completed_minutes == expected_minutes
    assert (
        result.before_reception_close.classification
        is OvertimeClassification.FULL_HOUR
    )
    assert result.after_reception_close.completed_minutes == 0


def test_crossing_reception_close_preserves_both_overtime_segments() -> None:
    result = classify_overtime(
        booking_ends_at=utc_dt(20, 30),
        checked_out_at=utc_dt(21, 20),
        local_checked_out_at=local_dt(18, 20),
        reception_closes_at=time(18, 0),
        reception_is_closed=False,
    )

    assert result.actual_overtime_seconds == 50 * 60
    assert result.completed_overtime_minutes == 50

    assert result.before_reception_close.actual_seconds == 30 * 60
    assert result.before_reception_close.completed_minutes == 30
    assert (
        result.before_reception_close.classification
        is OvertimeClassification.FULL_HOUR
    )

    assert result.after_reception_close.actual_seconds == 20 * 60
    assert result.after_reception_close.completed_minutes == 20
    assert (
        result.after_reception_close.classification
        is OvertimeClassification.PROPORTIONAL
    )


def test_checkout_exactly_at_reception_close_stays_before_close_segment() -> None:
    result = classify_overtime(
        booking_ends_at=utc_dt(20, 30),
        checked_out_at=utc_dt(21, 0),
        local_checked_out_at=local_dt(18, 0),
        reception_closes_at=time(18, 0),
        reception_is_closed=False,
    )

    assert result.completed_overtime_minutes == 30
    assert result.before_reception_close.completed_minutes == 30
    assert (
        result.before_reception_close.classification
        is OvertimeClassification.FULL_HOUR
    )
    assert result.after_reception_close.completed_minutes == 0
    assert result.after_reception_close.classification is OvertimeClassification.NONE


def test_overtime_starting_after_reception_close_is_fully_accounted_after_close() -> None:
    result = classify_overtime(
        booking_ends_at=utc_dt(21, 5),
        checked_out_at=utc_dt(21, 25),
        local_checked_out_at=local_dt(18, 25),
        reception_closes_at=time(18, 0),
        reception_is_closed=False,
    )

    assert result.actual_overtime_seconds == 20 * 60
    assert result.completed_overtime_minutes == 20
    assert result.before_reception_close.completed_minutes == 0

    assert result.after_reception_close.actual_seconds == 20 * 60
    assert result.after_reception_close.completed_minutes == 20
    assert (
        result.after_reception_close.classification
        is OvertimeClassification.PROPORTIONAL
    )


def test_closed_reception_day_preserves_all_overtime_for_later_decision() -> None:
    result = classify_overtime(
        booking_ends_at=utc_dt(16, 0),
        checked_out_at=utc_dt(16, 20),
        local_checked_out_at=local_dt(13, 20),
        reception_closes_at=None,
        reception_is_closed=True,
    )

    assert result.actual_overtime_seconds == 20 * 60
    assert result.completed_overtime_minutes == 20
    assert result.before_reception_close.completed_minutes == 0

    assert result.after_reception_close.actual_seconds == 20 * 60
    assert result.after_reception_close.completed_minutes == 20
    assert (
        result.after_reception_close.classification
        is OvertimeClassification.PROPORTIONAL
    )


def test_after_close_seconds_are_preserved_without_rounding_up() -> None:
    result = classify_overtime(
        booking_ends_at=utc_dt(20, 30),
        checked_out_at=utc_dt(21, 20, 59),
        local_checked_out_at=local_dt(18, 20, 59),
        reception_closes_at=time(18, 0),
        reception_is_closed=False,
    )

    assert result.actual_overtime_seconds == (50 * 60) + 59
    assert result.completed_overtime_minutes == 50

    assert result.before_reception_close.completed_minutes == 30
    assert result.after_reception_close.actual_seconds == (20 * 60) + 59
    assert result.after_reception_close.completed_minutes == 20


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
