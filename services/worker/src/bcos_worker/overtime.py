"""Temporal overtime classification for HUMAN APPROVED M7-A2-T1/T7/T10."""

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
    EXCLUDED_AFTER_RECEPTION_CLOSE = "EXCLUDED_AFTER_RECEPTION_CLOSE"


@dataclass(frozen=True, slots=True)
class OvertimeTemporalResult:
    classification: OvertimeClassification
    actual_overtime_seconds: int
    billable_overtime_minutes: int


def classify_overtime(
    *,
    booking_ends_at: datetime,
    checked_out_at: datetime,
    local_checked_out_at: datetime,
    reception_closes_at: time | None,
    reception_is_closed: bool,
) -> OvertimeTemporalResult:
    """Classify overtime without performing any monetary calculation."""

    if booking_ends_at.tzinfo is None or checked_out_at.tzinfo is None:
        raise OvertimeTemporalError(
            "booking_ends_at and checked_out_at must be timezone-aware"
        )

    if local_checked_out_at.tzinfo is None:
        raise OvertimeTemporalError("local_checked_out_at must be timezone-aware")

    elapsed_seconds = int((checked_out_at - booking_ends_at).total_seconds())

    if elapsed_seconds <= 0:
        return OvertimeTemporalResult(
            classification=OvertimeClassification.NONE,
            actual_overtime_seconds=max(elapsed_seconds, 0),
            billable_overtime_minutes=0,
        )

    whole_minutes = elapsed_seconds // 60

    if reception_is_closed:
        return OvertimeTemporalResult(
            classification=OvertimeClassification.EXCLUDED_AFTER_RECEPTION_CLOSE,
            actual_overtime_seconds=elapsed_seconds,
            billable_overtime_minutes=0,
        )

    if reception_closes_at is None:
        raise OvertimeTemporalError(
            "open reception day must define reception_closes_at"
        )

    local_close = datetime.combine(
        local_checked_out_at.date(),
        reception_closes_at,
        tzinfo=local_checked_out_at.tzinfo,
    )

    if local_checked_out_at > local_close:
        return OvertimeTemporalResult(
            classification=OvertimeClassification.EXCLUDED_AFTER_RECEPTION_CLOSE,
            actual_overtime_seconds=elapsed_seconds,
            billable_overtime_minutes=0,
        )

    if whole_minutes == 0:
        return OvertimeTemporalResult(
            classification=OvertimeClassification.NONE,
            actual_overtime_seconds=elapsed_seconds,
            billable_overtime_minutes=0,
        )

    if whole_minutes < 30:
        return OvertimeTemporalResult(
            classification=OvertimeClassification.PROPORTIONAL,
            actual_overtime_seconds=elapsed_seconds,
            billable_overtime_minutes=whole_minutes,
        )

    return OvertimeTemporalResult(
        classification=OvertimeClassification.FULL_HOUR,
        actual_overtime_seconds=elapsed_seconds,
        billable_overtime_minutes=whole_minutes,
    )
