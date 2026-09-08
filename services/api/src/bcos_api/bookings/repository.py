"""Tenant-scoped persistence for BCOS bookings."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.bookings.domain import Booking, BookingStatus


def _booking_from_row(row: dict[str, object]) -> Booking:
    """Map one database row to the Booking domain model."""

    return Booking(
        id=row["id"],  # type: ignore[arg-type]
        tenant_id=row["tenant_id"],  # type: ignore[arg-type]
        unit_id=row["unit_id"],  # type: ignore[arg-type]
        resource_id=row["resource_id"],  # type: ignore[arg-type]
        professional_id=row["professional_id"],  # type: ignore[arg-type]
        series_id=row["series_id"],  # type: ignore[arg-type]
        status=BookingStatus(row["status"]),  # type: ignore[arg-type]
        starts_at=row["starts_at"],  # type: ignore[arg-type]
        ends_at=row["ends_at"],  # type: ignore[arg-type]
        buffer_before_minutes=row["buffer_before_minutes"],  # type: ignore[arg-type]
        buffer_after_minutes=row["buffer_after_minutes"],  # type: ignore[arg-type]
        pricing_snapshot=row["pricing_snapshot"],  # type: ignore[arg-type]
        notes=row["notes"],  # type: ignore[arg-type]
        confirmed_at=row["confirmed_at"],  # type: ignore[arg-type]
        cancelled_at=row["cancelled_at"],  # type: ignore[arg-type]
        completed_at=row["completed_at"],  # type: ignore[arg-type]
    )


async def list_bookings(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    starts_from: datetime | None = None,
    starts_until: datetime | None = None,
    professional_id: UUID | None = None,
    resource_id: UUID | None = None,
    status: BookingStatus | None = None,
) -> list[Booking]:
    """List bookings within one tenant using frozen API filters."""

    result = await session.execute(
        text(
            """
            SELECT
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
            FROM bookings
            WHERE tenant_id = :tenant_id
              AND (:starts_from IS NULL OR starts_at >= :starts_from)
              AND (:starts_until IS NULL OR starts_at <= :starts_until)
              AND (
                    :professional_id IS NULL
                    OR professional_id = :professional_id
              )
              AND (:resource_id IS NULL OR resource_id = :resource_id)
              AND (:status IS NULL OR status = :status)
            ORDER BY starts_at, id
            """
        ),
        {
            "tenant_id": tenant_id,
            "starts_from": starts_from,
            "starts_until": starts_until,
            "professional_id": professional_id,
            "resource_id": resource_id,
            "status": status.value if status is not None else None,
        },
    )

    return [
        _booking_from_row(dict(row))
        for row in result.mappings().all()
    ]


async def get_booking(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    booking_id: UUID,
) -> Booking | None:
    """Load one booking without crossing tenant boundaries."""

    result = await session.execute(
        text(
            """
            SELECT
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
            FROM bookings
            WHERE id = :booking_id
              AND tenant_id = :tenant_id
            LIMIT 1
            """
        ),
        {
            "booking_id": booking_id,
            "tenant_id": tenant_id,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _booking_from_row(dict(row))


async def create_booking(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unit_id: UUID,
    resource_id: UUID,
    professional_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    buffer_before_minutes: int,
    buffer_after_minutes: int,
    pricing_snapshot: dict[str, Any],
    notes: str | None,
    series_id: UUID | None = None,
) -> Booking:
    """Persist one PENDING booking with its immutable server-side snapshot."""

    result = await session.execute(
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
            "series_id": series_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "buffer_before_minutes": buffer_before_minutes,
            "buffer_after_minutes": buffer_after_minutes,
            "pricing_snapshot": json.dumps(pricing_snapshot),
            "notes": notes,
        },
    )

    row = result.mappings().one()

    return _booking_from_row(dict(row))





async def confirm_booking(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    booking_id: UUID,
) -> Booking | None:
    """Acquire canonical occupancy and transition one PENDING booking to CONFIRMED."""

    result = await session.execute(
        text(
            """
            WITH pending_booking AS (
                SELECT
                    id,
                    tenant_id,
                    resource_id,
                    starts_at,
                    ends_at,
                    buffer_before_minutes,
                    buffer_after_minutes
                FROM bookings
                WHERE id = :booking_id
                  AND tenant_id = :tenant_id
                  AND status = 'PENDING'
            ),
            acquired_occupancy AS (
                INSERT INTO resource_occupancies (
                    tenant_id,
                    resource_id,
                    period,
                    source_type,
                    source_id,
                    status
                )
                SELECT
                    tenant_id,
                    resource_id,
                    tstzrange(
                        starts_at
                            - make_interval(mins => buffer_before_minutes),
                        ends_at
                            + make_interval(mins => buffer_after_minutes),
                        '[)'
                    ),
                    'BOOKING',
                    id,
                    'ACTIVE'
                FROM pending_booking
                RETURNING source_id
            )
            UPDATE bookings AS b
            SET
                status = 'CONFIRMED',
                confirmed_at = now(),
                updated_at = now()
            FROM acquired_occupancy AS occupancy
            WHERE b.id = occupancy.source_id
              AND b.id = :booking_id
              AND b.tenant_id = :tenant_id
              AND b.status = 'PENDING'
            RETURNING
                b.id,
                b.tenant_id,
                b.unit_id,
                b.resource_id,
                b.professional_id,
                b.series_id,
                b.status,
                b.starts_at,
                b.ends_at,
                b.buffer_before_minutes,
                b.buffer_after_minutes,
                b.pricing_snapshot,
                b.notes,
                b.confirmed_at,
                b.cancelled_at,
                b.completed_at
            """
        ),
        {
            "booking_id": booking_id,
            "tenant_id": tenant_id,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _booking_from_row(dict(row))


async def cancel_booking(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    booking_id: UUID,
) -> Booking | None:
    """Cancel one PENDING or CONFIRMED booking and release occupancy if present."""

    result = await session.execute(
        text(
            """
            WITH cancellable_booking AS (
                SELECT
                    id,
                    tenant_id,
                    status
                FROM bookings
                WHERE id = :booking_id
                  AND tenant_id = :tenant_id
                  AND status IN ('PENDING', 'CONFIRMED')
            ),
            released_occupancy AS (
                UPDATE resource_occupancies AS ro
                SET
                    status = 'RELEASED',
                    released_at = now()
                FROM cancellable_booking AS cb
                WHERE cb.status = 'CONFIRMED'
                  AND ro.tenant_id = cb.tenant_id
                  AND ro.source_type = 'BOOKING'
                  AND ro.source_id = cb.id
                  AND ro.status = 'ACTIVE'
                RETURNING ro.source_id
            )
            UPDATE bookings AS b
            SET
                status = 'CANCELLED',
                cancelled_at = now(),
                updated_at = now()
            FROM cancellable_booking AS cb
            WHERE b.id = cb.id
              AND b.tenant_id = cb.tenant_id
              AND (
                    cb.status = 'PENDING'
                    OR EXISTS (
                        SELECT 1
                        FROM released_occupancy AS released
                        WHERE released.source_id = cb.id
                    )
              )
            RETURNING
                b.id,
                b.tenant_id,
                b.unit_id,
                b.resource_id,
                b.professional_id,
                b.series_id,
                b.status,
                b.starts_at,
                b.ends_at,
                b.buffer_before_minutes,
                b.buffer_after_minutes,
                b.pricing_snapshot,
                b.notes,
                b.confirmed_at,
                b.cancelled_at,
                b.completed_at
            """
        ),
        {
            "booking_id": booking_id,
            "tenant_id": tenant_id,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _booking_from_row(dict(row))



async def extend_booking(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    booking_id: UUID,
    ends_at: datetime,
) -> Booking | None:
    """Extend one CONFIRMED booking and its canonical occupancy atomically."""

    result = await session.execute(
        text(
            """
            WITH extendable_booking AS (
                SELECT
                    id,
                    tenant_id,
                    starts_at,
                    buffer_before_minutes,
                    buffer_after_minutes
                FROM bookings
                WHERE id = :booking_id
                  AND tenant_id = :tenant_id
                  AND status = 'CONFIRMED'
                  AND :ends_at > starts_at
            ),
            updated_occupancy AS (
                UPDATE resource_occupancies AS ro
                SET period = tstzrange(
                    eb.starts_at
                        - make_interval(mins => eb.buffer_before_minutes),
                    :ends_at
                        + make_interval(mins => eb.buffer_after_minutes),
                    '[)'
                )
                FROM extendable_booking AS eb
                WHERE ro.tenant_id = eb.tenant_id
                  AND ro.source_type = 'BOOKING'
                  AND ro.source_id = eb.id
                  AND ro.status = 'ACTIVE'
                RETURNING ro.source_id
            )
            UPDATE bookings AS b
            SET
                ends_at = :ends_at,
                updated_at = now()
            FROM extendable_booking AS eb
            WHERE b.id = eb.id
              AND b.tenant_id = eb.tenant_id
              AND EXISTS (
                    SELECT 1
                    FROM updated_occupancy AS occupancy
                    WHERE occupancy.source_id = eb.id
              )
            RETURNING
                b.id,
                b.tenant_id,
                b.unit_id,
                b.resource_id,
                b.professional_id,
                b.series_id,
                b.status,
                b.starts_at,
                b.ends_at,
                b.buffer_before_minutes,
                b.buffer_after_minutes,
                b.pricing_snapshot,
                b.notes,
                b.confirmed_at,
                b.cancelled_at,
                b.completed_at
            """
        ),
        {
            "booking_id": booking_id,
            "tenant_id": tenant_id,
            "ends_at": ends_at,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _booking_from_row(dict(row))


async def has_active_occupancy_conflict(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    resource_id: UUID,
    periods: list[tuple[datetime, datetime]],
) -> bool:
    """Check whether any proposed physical period overlaps ACTIVE occupancy."""

    if not periods:
        return False

    starts_at = [period[0] for period in periods]
    ends_at = [period[1] for period in periods]

    result = await session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM resource_occupancies AS ro
                CROSS JOIN unnest(
                    CAST(:starts_at AS timestamptz[]),
                    CAST(:ends_at AS timestamptz[])
                ) AS proposed(starts_at, ends_at)
                WHERE ro.tenant_id = :tenant_id
                  AND ro.resource_id = :resource_id
                  AND ro.status = 'ACTIVE'
                  AND ro.period && tstzrange(
                      proposed.starts_at,
                      proposed.ends_at,
                      '[)'
                  )
            )
            """
        ),
        {
            "tenant_id": tenant_id,
            "resource_id": resource_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
    )

    return bool(result.scalar_one())
