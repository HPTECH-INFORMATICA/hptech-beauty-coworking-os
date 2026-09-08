"""SQL repository for BCOS booking series."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.bookings.domain import Booking, BookingStatus
from bcos_api.bookings.series_domain import BookingSeries


def _series_from_row(row: Any) -> BookingSeries:
    """Map one SQL row to the booking-series domain model."""

    return BookingSeries(
        id=row.id,
        tenant_id=row.tenant_id,
        professional_id=row.professional_id,
        rrule=row.rrule,
        timezone=row.timezone,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        cancelled_at=row.cancelled_at,
    )


def _booking_from_row(row: Any) -> Booking:
    """Map one SQL row to the booking domain model."""

    return Booking(
        id=row.id,
        tenant_id=row.tenant_id,
        unit_id=row.unit_id,
        resource_id=row.resource_id,
        professional_id=row.professional_id,
        series_id=row.series_id,
        status=BookingStatus(row.status),
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        buffer_before_minutes=row.buffer_before_minutes,
        buffer_after_minutes=row.buffer_after_minutes,
        pricing_snapshot=row.pricing_snapshot,
        notes=row.notes,
        confirmed_at=row.confirmed_at,
        cancelled_at=row.cancelled_at,
        completed_at=row.completed_at,
    )


async def get_booking_series(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    series_id: UUID,
) -> BookingSeries | None:
    """Return one booking series scoped to its tenant."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                professional_id,
                rrule,
                timezone,
                starts_at,
                ends_at,
                cancelled_at
            FROM booking_series
            WHERE tenant_id = :tenant_id
              AND id = :series_id
            """
        ),
        {
            "tenant_id": tenant_id,
            "series_id": series_id,
        },
    )

    row = result.one_or_none()

    if row is None:
        return None

    return _series_from_row(row)


async def create_booking_series(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unit_id: UUID,
    resource_id: UUID,
    professional_id: UUID,
    rrule: str,
    timezone: str,
    starts_at: datetime,
    ends_at: datetime,
    buffer_before_minutes: int,
    buffer_after_minutes: int,
    notes: str | None,
    occurrences: list[tuple[datetime, datetime, dict[str, Any]]],
) -> tuple[BookingSeries, list[Booking]]:
    """Persist one series and all of its PENDING booking occurrences."""

    series_result = await session.execute(
        text(
            """
            INSERT INTO booking_series (
                tenant_id,
                professional_id,
                rrule,
                timezone,
                starts_at,
                ends_at
            )
            VALUES (
                :tenant_id,
                :professional_id,
                :rrule,
                :timezone,
                :starts_at,
                :ends_at
            )
            RETURNING
                id,
                tenant_id,
                professional_id,
                rrule,
                timezone,
                starts_at,
                ends_at,
                cancelled_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "professional_id": professional_id,
            "rrule": rrule,
            "timezone": timezone,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
    )

    series = _series_from_row(series_result.one())
    bookings: list[Booking] = []

    for occurrence_start, occurrence_end, pricing_snapshot in occurrences:
        booking_result = await session.execute(
            text(
                """
                INSERT INTO bookings (
                    tenant_id,
                    unit_id,
                    resource_id,
                    professional_id,
                    series_id,
                    status,
                    starts_at,
                    ends_at,
                    buffer_before_minutes,
                    buffer_after_minutes,
                    pricing_snapshot,
                    notes
                )
                VALUES (
                    :tenant_id,
                    :unit_id,
                    :resource_id,
                    :professional_id,
                    :series_id,
                    'PENDING',
                    :starts_at,
                    :ends_at,
                    :buffer_before_minutes,
                    :buffer_after_minutes,
                    CAST(:pricing_snapshot AS jsonb),
                    :notes
                )
                RETURNING
                    id,
                    tenant_id,
                    unit_id,
                    resource_id,
                    professional_id,
                    series_id,
                    status,
                    starts_at,
                    ends_at,
                    buffer_before_minutes,
                    buffer_after_minutes,
                    pricing_snapshot,
                    notes,
                    confirmed_at,
                    cancelled_at,
                    completed_at
                """
            ),
            {
                "tenant_id": tenant_id,
                "unit_id": unit_id,
                "resource_id": resource_id,
                "professional_id": professional_id,
                "series_id": series.id,
                "starts_at": occurrence_start,
                "ends_at": occurrence_end,
                "buffer_before_minutes": buffer_before_minutes,
                "buffer_after_minutes": buffer_after_minutes,
                "pricing_snapshot": json.dumps(pricing_snapshot),
                "notes": notes,
            },
        )

        bookings.append(_booking_from_row(booking_result.one()))

    return series, bookings


async def cancel_booking_series(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    series_id: UUID,
) -> BookingSeries | None:
    """Cancel one active series and its future cancellable occurrences atomically."""

    result = await session.execute(
        text(
            """
            WITH cancellable_series AS (
                SELECT
                    id,
                    tenant_id
                FROM booking_series
                WHERE id = :series_id
                  AND tenant_id = :tenant_id
                  AND cancelled_at IS NULL
                FOR UPDATE
            ),
            future_bookings AS (
                SELECT
                    b.id,
                    b.tenant_id,
                    b.status
                FROM bookings AS b
                JOIN cancellable_series AS bs
                  ON bs.id = b.series_id
                 AND bs.tenant_id = b.tenant_id
                WHERE b.starts_at > now()
                  AND b.status IN ('PENDING', 'CONFIRMED')
                FOR UPDATE
            ),
            released_occupancies AS (
                UPDATE resource_occupancies AS ro
                SET
                    status = 'RELEASED',
                    released_at = now()
                FROM future_bookings AS fb
                WHERE fb.status = 'CONFIRMED'
                  AND ro.tenant_id = fb.tenant_id
                  AND ro.source_type = 'BOOKING'
                  AND ro.source_id = fb.id
                  AND ro.status = 'ACTIVE'
                RETURNING ro.source_id
            ),
            cancelled_bookings AS (
                UPDATE bookings AS b
                SET
                    status = 'CANCELLED',
                    cancelled_at = now(),
                    updated_at = now()
                FROM future_bookings AS fb
                WHERE b.id = fb.id
                  AND b.tenant_id = fb.tenant_id
                  AND (
                        fb.status = 'PENDING'
                        OR EXISTS (
                            SELECT 1
                            FROM released_occupancies AS released
                            WHERE released.source_id = fb.id
                        )
                  )
                RETURNING b.id
            ),
            series_guard AS (
                SELECT cs.id
                FROM cancellable_series AS cs
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM future_bookings AS fb
                    WHERE fb.status = 'CONFIRMED'
                      AND NOT EXISTS (
                          SELECT 1
                          FROM released_occupancies AS released
                          WHERE released.source_id = fb.id
                      )
                )
            )
            UPDATE booking_series AS bs
            SET
                cancelled_at = now(),
                updated_at = now()
            FROM series_guard AS guard
            WHERE bs.id = guard.id
              AND bs.tenant_id = :tenant_id
            RETURNING
                bs.id,
                bs.tenant_id,
                bs.professional_id,
                bs.rrule,
                bs.timezone,
                bs.starts_at,
                bs.ends_at,
                bs.cancelled_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "series_id": series_id,
        },
    )

    row = result.one_or_none()

    if row is None:
        return None

    return _series_from_row(row)
