"""Tenant-safe hydration for USAGE_COMPLETED pricing context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PricingContextError(RuntimeError):
    """Raised when authoritative pricing context cannot be hydrated safely."""


@dataclass(frozen=True, slots=True)
class ReceptionHours:
    day_of_week: int
    opens_at: time | None
    closes_at: time | None
    is_closed: bool


@dataclass(frozen=True, slots=True)
class UsagePricingContext:
    tenant_id: UUID
    usage_id: UUID
    booking_id: UUID
    resource_id: UUID
    professional_id: UUID
    unit_id: UUID
    usage_status: str
    checked_in_at: datetime
    checked_out_at: datetime
    booking_starts_at: datetime
    booking_ends_at: datetime
    pricing_snapshot: dict[str, Any]
    unit_timezone: str
    local_checked_out_at: datetime
    reception_hours: ReceptionHours


async def hydrate_usage_pricing_context(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    usage_id: UUID,
) -> UsagePricingContext:
    """Load the authoritative, tenant-safe context for a completed usage."""

    result = await session.execute(
        text(
            """
            SELECT
                u.id AS usage_id,
                u.tenant_id,
                u.booking_id,
                u.resource_id,
                u.professional_id,
                u.status::text AS usage_status,
                u.checked_in_at,
                u.checked_out_at,
                b.unit_id,
                b.starts_at AS booking_starts_at,
                b.ends_at AS booking_ends_at,
                b.pricing_snapshot,
                un.timezone AS unit_timezone
            FROM usages AS u
            JOIN bookings AS b
              ON b.id = u.booking_id
             AND b.tenant_id = u.tenant_id
            JOIN units AS un
              ON un.id = b.unit_id
             AND un.tenant_id = u.tenant_id
            WHERE u.id = :usage_id
              AND u.tenant_id = :tenant_id
            """
        ),
        {
            "usage_id": usage_id,
            "tenant_id": tenant_id,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        raise PricingContextError(
            "completed usage pricing context not found for tenant"
        )

    if row["usage_status"] != "COMPLETED":
        raise PricingContextError("usage must be COMPLETED before pricing")

    checked_in_at = row["checked_in_at"]
    checked_out_at = row["checked_out_at"]

    if checked_in_at is None or checked_out_at is None:
        raise PricingContextError(
            "completed usage must have checked_in_at and checked_out_at"
        )

    if checked_in_at.tzinfo is None or checked_out_at.tzinfo is None:
        raise PricingContextError("usage timestamps must be timezone-aware")

    raw_snapshot = row["pricing_snapshot"]
    if not isinstance(raw_snapshot, dict):
        raise PricingContextError("booking pricing_snapshot must be an object")

    unit_timezone = row["unit_timezone"]
    if not isinstance(unit_timezone, str) or not unit_timezone.strip():
        raise PricingContextError("unit timezone must be configured")

    try:
        zone = ZoneInfo(unit_timezone)
    except ZoneInfoNotFoundError:
        raise PricingContextError("unit timezone must be a valid IANA timezone") from None

    local_checked_out_at = checked_out_at.astimezone(zone)
    day_of_week = local_checked_out_at.weekday()

    reception_result = await session.execute(
        text(
            """
            SELECT
                rh.day_of_week,
                rh.opens_at,
                rh.closes_at,
                rh.is_closed
            FROM unit_reception_hours AS rh
            WHERE rh.tenant_id = :tenant_id
              AND rh.unit_id = :unit_id
              AND rh.day_of_week = :day_of_week
            """
        ),
        {
            "tenant_id": tenant_id,
            "unit_id": row["unit_id"],
            "day_of_week": day_of_week,
        },
    )

    reception_row = reception_result.mappings().one_or_none()

    if reception_row is None:
        raise PricingContextError(
            "reception hours configuration missing for local checkout day"
        )

    return UsagePricingContext(
        tenant_id=row["tenant_id"],
        usage_id=row["usage_id"],
        booking_id=row["booking_id"],
        resource_id=row["resource_id"],
        professional_id=row["professional_id"],
        unit_id=row["unit_id"],
        usage_status=row["usage_status"],
        checked_in_at=checked_in_at,
        checked_out_at=checked_out_at,
        booking_starts_at=row["booking_starts_at"],
        booking_ends_at=row["booking_ends_at"],
        pricing_snapshot=dict(raw_snapshot),
        unit_timezone=unit_timezone,
        local_checked_out_at=local_checked_out_at,
        reception_hours=ReceptionHours(
            day_of_week=reception_row["day_of_week"],
            opens_at=reception_row["opens_at"],
            closes_at=reception_row["closes_at"],
            is_closed=reception_row["is_closed"],
        ),
    )
