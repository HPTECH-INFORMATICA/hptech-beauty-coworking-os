"""Reception-hours domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from uuid import UUID


class InvalidReceptionHours(Exception):
    """Raised when reception-hours domain data is invalid."""


@dataclass(frozen=True)
class ReceptionHours:
    """Reception operating window for one unit and weekday."""

    id: UUID
    tenant_id: UUID
    unit_id: UUID
    day_of_week: int
    opens_at: time | None
    closes_at: time | None
    is_closed: bool


def validate_reception_hours(
    *,
    day_of_week: int,
    opens_at: time | None,
    closes_at: time | None,
    is_closed: bool,
) -> tuple[int, time | None, time | None, bool]:
    """Validate one reception-hours entry."""

    if day_of_week < 0 or day_of_week > 6:
        raise InvalidReceptionHours(
            "day_of_week must be between 0 and 6."
        )

    if is_closed:
        if opens_at is not None or closes_at is not None:
            raise InvalidReceptionHours(
                "Closed reception hours must not define opening or closing times."
            )

        return day_of_week, None, None, True

    if opens_at is None or closes_at is None:
        raise InvalidReceptionHours(
            "Open reception hours require opening and closing times."
        )

    if opens_at >= closes_at:
        raise InvalidReceptionHours(
            "Reception opening time must be earlier than closing time."
        )

    return day_of_week, opens_at, closes_at, False
