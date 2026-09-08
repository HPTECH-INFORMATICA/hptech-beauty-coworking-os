"""Tenant-scoped persistence for BCOS Usage."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.usages.domain import Usage, UsageStatus


def _usage_from_row(row: dict[str, object]) -> Usage:
    """Map one database row to the Usage domain model."""

    return Usage(
        id=row["id"],  # type: ignore[arg-type]
        tenant_id=row["tenant_id"],  # type: ignore[arg-type]
        booking_id=row["booking_id"],  # type: ignore[arg-type]
        resource_id=row["resource_id"],  # type: ignore[arg-type]
        professional_id=row["professional_id"],  # type: ignore[arg-type]
        status=UsageStatus(row["status"]),  # type: ignore[arg-type]
        checked_in_at=row["checked_in_at"],  # type: ignore[arg-type]
        checked_out_at=row["checked_out_at"],  # type: ignore[arg-type]
    )


async def get_usage(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    usage_id: UUID,
) -> Usage | None:
    """Load one Usage without crossing tenant boundaries."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                booking_id,
                resource_id,
                professional_id,
                status,
                checked_in_at,
                checked_out_at
            FROM usages
            WHERE id = :usage_id
              AND tenant_id = :tenant_id
            LIMIT 1
            """
        ),
        {
            "usage_id": usage_id,
            "tenant_id": tenant_id,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _usage_from_row(dict(row))


async def get_usage_by_booking(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    booking_id: UUID,
) -> Usage | None:
    """Load the Usage associated with one Booking in the tenant."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                booking_id,
                resource_id,
                professional_id,
                status,
                checked_in_at,
                checked_out_at
            FROM usages
            WHERE tenant_id = :tenant_id
              AND booking_id = :booking_id
            LIMIT 1
            """
        ),
        {
            "tenant_id": tenant_id,
            "booking_id": booking_id,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _usage_from_row(dict(row))


async def create_checked_in_usage(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    booking_id: UUID,
    checked_in_at: datetime,
) -> Usage | None:
    """Create CHECKED_IN Usage only from a CONFIRMED tenant Booking."""

    result = await session.execute(
        text(
            """
            INSERT INTO usages (
                tenant_id,
                booking_id,
                resource_id,
                professional_id,
                status,
                checked_in_at
            )
            SELECT
                tenant_id,
                id,
                resource_id,
                professional_id,
                'CHECKED_IN',
                :checked_in_at
            FROM bookings
            WHERE id = :booking_id
              AND tenant_id = :tenant_id
              AND status = 'CONFIRMED'
            RETURNING
                id,
                tenant_id,
                booking_id,
                resource_id,
                professional_id,
                status,
                checked_in_at,
                checked_out_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "booking_id": booking_id,
            "checked_in_at": checked_in_at,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _usage_from_row(dict(row))


async def complete_usage_with_outbox(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    usage_id: UUID,
    checked_out_at: datetime,
) -> Usage | None:
    """Complete Usage, Booking, occupancy and Outbox atomically."""

    dedupe_key = f"usage-completed:{usage_id}"

    result = await session.execute(
        text(
            """
            WITH usage_to_complete AS (
                SELECT
                    u.id,
                    u.tenant_id,
                    u.booking_id,
                    u.resource_id,
                    u.professional_id,
                    u.checked_in_at
                FROM usages AS u
                WHERE u.id = :usage_id
                  AND u.tenant_id = :tenant_id
                  AND u.status = 'CHECKED_IN'
                  AND :checked_out_at >= u.checked_in_at
                FOR UPDATE
            ),
            released_occupancy AS (
                UPDATE resource_occupancies AS ro
                SET
                    status = 'RELEASED',
                    released_at = :checked_out_at
                FROM usage_to_complete AS utc
                WHERE ro.tenant_id = utc.tenant_id
                  AND ro.source_type = 'BOOKING'
                  AND ro.source_id = utc.booking_id
                  AND ro.status = 'ACTIVE'
                RETURNING ro.source_id
            ),
            completed_booking AS (
                UPDATE bookings AS b
                SET
                    status = 'COMPLETED',
                    completed_at = :checked_out_at,
                    updated_at = now()
                FROM usage_to_complete AS utc
                WHERE b.id = utc.booking_id
                  AND b.tenant_id = utc.tenant_id
                  AND b.status = 'CONFIRMED'
                  AND EXISTS (
                      SELECT 1
                      FROM released_occupancy AS ro
                      WHERE ro.source_id = utc.booking_id
                  )
                RETURNING b.id
            ),
            completed_usage AS (
                UPDATE usages AS u
                SET
                    status = 'COMPLETED',
                    checked_out_at = :checked_out_at,
                    updated_at = now()
                FROM usage_to_complete AS utc
                WHERE u.id = utc.id
                  AND u.tenant_id = utc.tenant_id
                  AND EXISTS (
                      SELECT 1
                      FROM completed_booking AS cb
                      WHERE cb.id = utc.booking_id
                  )
                  AND :checked_out_at >= utc.checked_in_at
                RETURNING
                    u.id,
                    u.tenant_id,
                    u.booking_id,
                    u.resource_id,
                    u.professional_id,
                    u.status,
                    u.checked_in_at,
                    u.checked_out_at
            ),
            outbox_insert AS (
                INSERT INTO outbox_events (
                    tenant_id,
                    dedupe_key,
                    event_type,
                    aggregate_type,
                    aggregate_id,
                    payload
                )
                SELECT
                    cu.tenant_id,
                    :dedupe_key,
                    'USAGE_COMPLETED',
                    'USAGE',
                    cu.id,
                    CAST(:payload AS jsonb)
                FROM completed_usage AS cu
                RETURNING aggregate_id
            )
            SELECT
                cu.id,
                cu.tenant_id,
                cu.booking_id,
                cu.resource_id,
                cu.professional_id,
                cu.status,
                cu.checked_in_at,
                cu.checked_out_at
            FROM completed_usage AS cu
            JOIN outbox_insert AS oi
              ON oi.aggregate_id = cu.id
            """
        ),
        {
            "tenant_id": tenant_id,
            "usage_id": usage_id,
            "checked_out_at": checked_out_at,
            "dedupe_key": dedupe_key,
            "payload": json.dumps(
                {
                    "usage_id": str(usage_id),
                    "checked_out_at": checked_out_at.isoformat(),
                }
            ),
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _usage_from_row(dict(row))
