"""Booking-series domain rules and finite RRULE expansion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil.rrule import rrule as DateutilRRule
from dateutil.rrule import rrulestr


class InvalidBookingSeries(Exception):
    """Raised when booking-series domain data is invalid."""


@dataclass(frozen=True)
class BookingSeries:
    """Recurring booking series persisted by BCOS."""

    id: UUID
    tenant_id: UUID
    professional_id: UUID
    rrule: str
    timezone: str
    starts_at: datetime
    ends_at: datetime | None
    cancelled_at: datetime | None


@dataclass(frozen=True)
class BookingOccurrence:
    """One materialized occurrence produced from a finite RRULE."""

    starts_at: datetime
    ends_at: datetime


def _normalize_finite_rrule(value: str) -> str:
    """Validate the V1 RRULE envelope without relying on dateutil internals."""

    normalized = value.strip()

    if not normalized:
        raise InvalidBookingSeries("rrule must not be blank.")

    if "\r" in normalized or "\n" in normalized:
        raise InvalidBookingSeries(
            "rrule must contain exactly one recurrence rule."
        )

    if normalized.upper().startswith("RRULE:"):
        normalized = normalized[6:].strip()

    if not normalized:
        raise InvalidBookingSeries("rrule must not be blank.")

    parts = normalized.split(";")
    properties: dict[str, str] = {}

    for part in parts:
        if "=" not in part:
            raise InvalidBookingSeries("rrule is invalid.")

        key, value = part.split("=", 1)
        key = key.strip().upper()
        value = value.strip()

        if not key or not value:
            raise InvalidBookingSeries("rrule is invalid.")

        if key in properties:
            raise InvalidBookingSeries(
                "rrule must not repeat properties."
            )

        properties[key] = value

    if "FREQ" not in properties:
        raise InvalidBookingSeries("rrule must define FREQ.")

    has_count = "COUNT" in properties
    has_until = "UNTIL" in properties

    if not has_count and not has_until:
        raise InvalidBookingSeries(
            "rrule must be finite using COUNT or UNTIL."
        )

    if has_count and has_until:
        raise InvalidBookingSeries(
            "rrule must not define both COUNT and UNTIL."
        )

    return ";".join(
        f"{key}={value}"
        for key, value in (
            part.split("=", 1)
            for part in normalized.split(";")
        )
    )


def validate_occurrences_do_not_overlap(
    occurrences: list[BookingOccurrence],
) -> None:
    """Reject recurring business intervals that overlap."""

    ordered = sorted(
        occurrences,
        key=lambda occurrence: occurrence.starts_at,
    )

    for previous, current in zip(ordered, ordered[1:], strict=False):
        if current.starts_at < previous.ends_at:
            raise InvalidBookingSeries(
                "rrule produces overlapping booking occurrences."
            )


def validate_physical_periods_do_not_overlap(
    periods: list[tuple[datetime, datetime]],
) -> None:
    """Reject physical intervals that overlap after resource buffers."""

    ordered = sorted(periods, key=lambda period: period[0])

    for previous, current in zip(ordered, ordered[1:], strict=False):
        if current[0] < previous[1]:
            raise InvalidBookingSeries(
                "booking occurrences overlap after resource buffers."
            )


def expand_booking_occurrences(
    *,
    starts_at: datetime,
    duration_minutes: int,
    rrule: str,
    timezone: str,
) -> list[BookingOccurrence]:
    """Expand one finite V1 RRULE into timezone-aware occurrences."""

    if starts_at.tzinfo is None or starts_at.utcoffset() is None:
        raise InvalidBookingSeries("starts_at must be timezone-aware.")

    if duration_minutes < 1:
        raise InvalidBookingSeries(
            "duration_minutes must be at least 1."
        )

    normalized_timezone = timezone.strip()

    if not normalized_timezone:
        raise InvalidBookingSeries("timezone must not be blank.")

    try:
        series_timezone = ZoneInfo(normalized_timezone)
    except ZoneInfoNotFoundError as exc:
        raise InvalidBookingSeries(
            "timezone must be a valid IANA timezone."
        ) from exc

    normalized_rrule = _normalize_finite_rrule(rrule)
    local_start = starts_at.astimezone(series_timezone)

    try:
        parsed_rule = rrulestr(
            normalized_rrule,
            dtstart=local_start,
        )
    except (TypeError, ValueError) as exc:
        raise InvalidBookingSeries("rrule is invalid.") from exc

    if not isinstance(parsed_rule, DateutilRRule):
        raise InvalidBookingSeries(
            "rrule must contain exactly one recurrence rule."
        )

    try:
        occurrence_starts = list(parsed_rule)
    except (OverflowError, TypeError, ValueError) as exc:
        raise InvalidBookingSeries(
            "rrule could not be expanded."
        ) from exc

    if not occurrence_starts:
        raise InvalidBookingSeries(
            "rrule must produce at least one occurrence."
        )

    duration = timedelta(minutes=duration_minutes)

    occurrences = [
        BookingOccurrence(
            starts_at=occurrence_start,
            ends_at=occurrence_start + duration,
        )
        for occurrence_start in occurrence_starts
    ]

    validate_occurrences_do_not_overlap(occurrences)

    return occurrences
