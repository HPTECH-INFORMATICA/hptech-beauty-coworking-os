"""Temporal overtime classification for HUMAN APPROVED M7-A2-T1/T7/T10/T11."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum


class OvertimeTemporalError(ValueError):
    """Raised when temporal overtime inputs are invalid."""


class OvertimeClassification(StrEnum):
    NONE = "NONE"
    PROPORTIONAL = "PROPORTIONAL"
    FULL_HOUR = "FULL_HOUR"


@dataclass(frozen=True, slots=True)
class OvertimeSegment:
    actual_seconds: int
    completed_minutes: int
    classification: OvertimeClassification


@dataclass(frozen=True, slots=True)
class OvertimeTemporalResult:
    actual_overtime_seconds: int
    completed_overtime_minutes: int
    before_reception_close: OvertimeSegment
    after_reception_close: OvertimeSegment


def _segment(
    seconds: int,
    *,
    proportional_until_minutes: int,
    full_hour_from_minutes: int,
) -> OvertimeSegment:
    safe_seconds = max(seconds, 0)
    completed_minutes = safe_seconds // 60
    remainder_minutes = completed_minutes % 60

    if completed_minutes == 0:
        classification = OvertimeClassification.NONE
    elif completed_minutes >= 60:
        classification = OvertimeClassification.FULL_HOUR
    elif remainder_minutes <= proportional_until_minutes:
        classification = OvertimeClassification.PROPORTIONAL
    elif remainder_minutes >= full_hour_from_minutes:
        classification = OvertimeClassification.FULL_HOUR
    else:
        raise OvertimeTemporalError(
            "overtime minutes are not covered by the configured proportional/full-hour rule"
        )

    return OvertimeSegment(
        actual_seconds=safe_seconds,
        completed_minutes=completed_minutes,
        classification=classification,
    )


def classify_overtime(
    *,
    booking_ends_at: datetime,
    checked_out_at: datetime,
    local_checked_out_at: datetime,
    reception_closes_at: time | None,
    reception_is_closed: bool,
    proportional_until_minutes: int,
    full_hour_from_minutes: int,
) -> OvertimeTemporalResult:
    """Segment overtime without performing any monetary calculation."""

    if booking_ends_at.tzinfo is None or checked_out_at.tzinfo is None:
        raise OvertimeTemporalError(
            "booking_ends_at and checked_out_at must be timezone-aware"
        )

    if local_checked_out_at.tzinfo is None:
        raise OvertimeTemporalError("local_checked_out_at must be timezone-aware")

    elapsed_seconds = int((checked_out_at - booking_ends_at).total_seconds())

    if elapsed_seconds <= 0:
        empty = _segment(
            0,
            proportional_until_minutes=proportional_until_minutes,
            full_hour_from_minutes=full_hour_from_minutes,
        )
        return OvertimeTemporalResult(
            actual_overtime_seconds=0,
            completed_overtime_minutes=0,
            before_reception_close=empty,
            after_reception_close=empty,
        )

    if reception_is_closed:
        after_close = _segment(
            elapsed_seconds,
            proportional_until_minutes=proportional_until_minutes,
            full_hour_from_minutes=full_hour_from_minutes,
        )
        return OvertimeTemporalResult(
            actual_overtime_seconds=elapsed_seconds,
            completed_overtime_minutes=elapsed_seconds // 60,
            before_reception_close=_segment(
            0,
            proportional_until_minutes=proportional_until_minutes,
            full_hour_from_minutes=full_hour_from_minutes,
        ),
            after_reception_close=after_close,
        )

    if reception_closes_at is None:
        raise OvertimeTemporalError(
            "open reception day must define reception_closes_at"
        )

    local_booking_end = booking_ends_at.astimezone(local_checked_out_at.tzinfo)

    local_close = datetime.combine(
        local_checked_out_at.date(),
        reception_closes_at,
        tzinfo=local_checked_out_at.tzinfo,
    )

    before_close_seconds = 0
    after_close_seconds = 0

    if local_booking_end >= local_close:
        after_close_seconds = elapsed_seconds
    elif local_checked_out_at <= local_close:
        before_close_seconds = elapsed_seconds
    else:
        before_close_seconds = int(
            (local_close - local_booking_end).total_seconds()
        )
        after_close_seconds = int(
            (local_checked_out_at - local_close).total_seconds()
        )

    before_close = _segment(
        before_close_seconds,
        proportional_until_minutes=proportional_until_minutes,
        full_hour_from_minutes=full_hour_from_minutes,
    )
    after_close = _segment(
        after_close_seconds,
        proportional_until_minutes=proportional_until_minutes,
        full_hour_from_minutes=full_hour_from_minutes,
    )

    return OvertimeTemporalResult(
        actual_overtime_seconds=elapsed_seconds,
        completed_overtime_minutes=elapsed_seconds // 60,
        before_reception_close=before_close,
        after_reception_close=after_close,
    )
