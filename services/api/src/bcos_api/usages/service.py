"""Usage application service for BCOS."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.bookings.domain import BookingStatus
from bcos_api.bookings.repository import get_booking
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.rbac import Permission, require_permission
from bcos_api.usages.domain import (
    Usage,
    UsageStatus,
    validate_check_in_timestamp,
    validate_check_out_timestamp,
)
from bcos_api.usages.repository import (
    complete_usage_with_outbox,
    create_checked_in_usage,
    get_usage,
    get_usage_by_booking,
)


class UsageNotFound(Exception):
    """Raised when a Usage or eligible Booking cannot be found in the tenant."""


class UsageConflict(Exception):
    """Raised when a Usage operation conflicts with the current state."""


def _actual_timestamp(value: datetime | None) -> datetime:
    """Use an explicit actual timestamp or the current UTC instant."""

    actual = value if value is not None else datetime.now(UTC)
    validate_check_in_timestamp(actual)
    return actual


async def check_in(
    session: AsyncSession,
    *,
    context: TenantContext,
    booking_id: UUID,
    checked_in_at: datetime | None = None,
) -> Usage:
    """Create the real Usage for one confirmed Booking."""

    require_permission(context, Permission.OPERATIONS)

    booking = await get_booking(
        session,
        tenant_id=context.tenant_id,
        booking_id=booking_id,
    )

    if booking is None:
        raise UsageNotFound("Booking does not exist in the tenant.")

    if booking.status is not BookingStatus.CONFIRMED:
        raise UsageConflict("Booking must be CONFIRMED before check-in.")

    existing_usage = await get_usage_by_booking(
        session,
        tenant_id=context.tenant_id,
        booking_id=booking_id,
    )

    if existing_usage is not None:
        raise UsageConflict("Booking already has a Usage.")

    actual_checked_in_at = _actual_timestamp(checked_in_at)

    usage = await create_checked_in_usage(
        session,
        tenant_id=context.tenant_id,
        booking_id=booking_id,
        checked_in_at=actual_checked_in_at,
    )

    if usage is None:
        raise UsageConflict("Booking is no longer eligible for check-in.")

    return usage


async def check_out(
    session: AsyncSession,
    *,
    context: TenantContext,
    usage_id: UUID,
    checked_out_at: datetime | None = None,
) -> Usage:
    """Complete one active Usage and emit USAGE_COMPLETED atomically."""

    require_permission(context, Permission.OPERATIONS)

    usage = await get_usage(
        session,
        tenant_id=context.tenant_id,
        usage_id=usage_id,
    )

    if usage is None:
        raise UsageNotFound("Usage does not exist in the tenant.")

    if usage.status is not UsageStatus.CHECKED_IN:
        raise UsageConflict("Usage must be CHECKED_IN before check-out.")

    if usage.checked_in_at is None:
        raise UsageConflict("CHECKED_IN Usage is missing checked_in_at.")

    actual_checked_out_at = (
        checked_out_at if checked_out_at is not None else datetime.now(UTC)
    )

    validate_check_out_timestamp(
        checked_in_at=usage.checked_in_at,
        checked_out_at=actual_checked_out_at,
    )

    completed_usage = await complete_usage_with_outbox(
        session,
        tenant_id=context.tenant_id,
        usage_id=usage_id,
        checked_out_at=actual_checked_out_at,
    )

    if completed_usage is None:
        raise UsageConflict("Usage is no longer eligible for check-out.")

    return completed_usage
