"""Booking application service for BCOS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.audit.repository import create_audit_log
from bcos_api.bookings.domain import (
    Booking,
    BookingStatus,
    InvalidBooking,
    validate_booking_buffers,
    validate_booking_period,
)
from bcos_api.bookings.pricing import (
    PricingSnapshotProducer,
    PricingSnapshotRequest,
)
from bcos_api.bookings.repository import (
    cancel_booking as persist_cancel_booking,
)
from bcos_api.bookings.repository import (
    confirm_booking as persist_confirm_booking,
)
from bcos_api.bookings.repository import (
    create_booking as persist_create_booking,
)
from bcos_api.bookings.repository import (
    extend_booking as persist_extend_booking,
)
from bcos_api.bookings.repository import (
    get_booking as repository_get_booking,
)
from bcos_api.bookings.repository import has_active_occupancy_conflict
from bcos_api.bookings.repository import (
    list_bookings as repository_list_bookings,
)
from bcos_api.bookings.series_domain import (
    BookingSeries,
    InvalidBookingSeries,
    expand_booking_occurrences,
    validate_physical_periods_do_not_overlap,
)
from bcos_api.bookings.series_repository import (
    cancel_booking_series as persist_cancel_booking_series,
)
from bcos_api.bookings.series_repository import (
    create_booking_series as persist_create_booking_series,
)
from bcos_api.bookings.series_repository import (
    get_booking_series as repository_get_booking_series,
)
from bcos_api.professionals.domain import ProfessionalStatus
from bcos_api.professionals.repository import get_professional
from bcos_api.resources.repository import get_resource
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.rbac import Permission, require_permission
from bcos_api.units.repository import get_unit


class BookingNotFound(Exception):
    """Raised when a booking cannot be found within the tenant."""


class BookingConflict(Exception):
    """Raised when a booking operation conflicts with its current state."""


class BookingSeriesNotFound(Exception):
    """Raised when a booking series cannot be found within the tenant."""


class BookingSeriesConflict(Exception):
    """Raised when a booking series conflicts with its current state or occupancy."""


@dataclass(frozen=True)
class _BookingCreationContext:
    """Validated relations and immutable resource data for booking creation."""

    unit_id: UUID
    resource_id: UUID
    resource_category_id: UUID
    professional_id: UUID
    buffer_before_minutes: int
    buffer_after_minutes: int


async def _prepare_booking_creation(
    session: AsyncSession,
    *,
    context: TenantContext,
    unit_id: UUID,
    resource_id: UUID,
    professional_id: UUID,
) -> _BookingCreationContext:
    """Validate tenant relations and capture resource booking invariants."""

    unit = await get_unit(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
    )

    if unit is None:
        raise InvalidBooking("Unit does not exist in the tenant.")

    if not unit.active:
        raise BookingConflict("Unit is inactive.")

    resource = await get_resource(
        session,
        tenant_id=context.tenant_id,
        resource_id=resource_id,
    )

    if resource is None:
        raise InvalidBooking("Resource does not exist in the tenant.")

    if resource.unit_id != unit.id:
        raise InvalidBooking(
            "Resource does not belong to the requested unit."
        )

    if not resource.active:
        raise BookingConflict("Resource is inactive.")

    professional = await get_professional(
        session,
        tenant_id=context.tenant_id,
        professional_id=professional_id,
    )

    if professional is None:
        raise InvalidBooking(
            "Professional does not exist in the tenant."
        )

    if professional.status is not ProfessionalStatus.ACTIVE:
        raise BookingConflict("Professional is inactive.")

    validate_booking_buffers(
        resource.buffer_before_minutes,
        resource.buffer_after_minutes,
    )

    return _BookingCreationContext(
        unit_id=unit.id,
        resource_id=resource.id,
        resource_category_id=resource.category_id,
        professional_id=professional.id,
        buffer_before_minutes=resource.buffer_before_minutes,
        buffer_after_minutes=resource.buffer_after_minutes,
    )


async def list_bookings(
    session: AsyncSession,
    *,
    context: TenantContext,
    starts_from: datetime | None = None,
    starts_until: datetime | None = None,
    professional_id: UUID | None = None,
    resource_id: UUID | None = None,
    status: BookingStatus | None = None,
) -> list[Booking]:
    """List tenant bookings for an authorized operations user."""

    require_permission(context, Permission.OPERATIONS)

    if (
        starts_from is not None
        and (starts_from.tzinfo is None or starts_from.utcoffset() is None)
    ):
        raise InvalidBooking("starts_from must be timezone-aware.")

    if (
        starts_until is not None
        and (starts_until.tzinfo is None or starts_until.utcoffset() is None)
    ):
        raise InvalidBooking("starts_until must be timezone-aware.")

    if (
        starts_from is not None
        and starts_until is not None
        and starts_until < starts_from
    ):
        raise InvalidBooking(
            "starts_until must not be before starts_from."
        )

    return await repository_list_bookings(
        session,
        tenant_id=context.tenant_id,
        starts_from=starts_from,
        starts_until=starts_until,
        professional_id=professional_id,
        resource_id=resource_id,
        status=status,
    )


async def get_booking(
    session: AsyncSession,
    *,
    context: TenantContext,
    booking_id: UUID,
) -> Booking:
    """Load one tenant booking for an authorized operations user."""

    require_permission(context, Permission.OPERATIONS)

    booking = await repository_get_booking(
        session,
        tenant_id=context.tenant_id,
        booking_id=booking_id,
    )

    if booking is None:
        raise BookingNotFound("Booking not found.")

    return booking


async def create_booking(
    session: AsyncSession,
    *,
    context: TenantContext,
    unit_id: UUID,
    resource_id: UUID,
    professional_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    notes: str | None,
    pricing_snapshot_producer: PricingSnapshotProducer,
) -> Booking:
    """Create one PENDING booking using trusted server-side pricing."""

    require_permission(context, Permission.OPERATIONS)
    validate_booking_period(starts_at, ends_at)

    creation = await _prepare_booking_creation(
        session,
        context=context,
        unit_id=unit_id,
        resource_id=resource_id,
        professional_id=professional_id,
    )

    pricing_snapshot = await pricing_snapshot_producer.produce(
        PricingSnapshotRequest(
            tenant_id=context.tenant_id,
            unit_id=creation.unit_id,
            resource_id=creation.resource_id,
            resource_category_id=creation.resource_category_id,
            professional_id=creation.professional_id,
            starts_at=starts_at,
            ends_at=ends_at,
        )
    )

    if not pricing_snapshot:
        raise InvalidBooking(
            "Pricing snapshot must be a non-empty object."
        )

    return await persist_create_booking(
        session,
        tenant_id=context.tenant_id,
        unit_id=creation.unit_id,
        resource_id=creation.resource_id,
        professional_id=creation.professional_id,
        starts_at=starts_at,
        ends_at=ends_at,
        buffer_before_minutes=creation.buffer_before_minutes,
        buffer_after_minutes=creation.buffer_after_minutes,
        pricing_snapshot=pricing_snapshot,
        notes=notes,
    )


async def create_booking_series(
    session: AsyncSession,
    *,
    context: TenantContext,
    unit_id: UUID,
    resource_id: UUID,
    professional_id: UUID,
    starts_at: datetime,
    duration_minutes: int,
    rrule: str,
    timezone: str,
    notes: str | None,
    pricing_snapshot_producer: PricingSnapshotProducer,
) -> tuple[BookingSeries, list[Booking]]:
    """Create one finite series and all of its PENDING occurrences."""

    require_permission(context, Permission.OPERATIONS)

    occurrences = expand_booking_occurrences(
        starts_at=starts_at,
        duration_minutes=duration_minutes,
        rrule=rrule,
        timezone=timezone,
    )

    creation = await _prepare_booking_creation(
        session,
        context=context,
        unit_id=unit_id,
        resource_id=resource_id,
        professional_id=professional_id,
    )

    buffer_before = timedelta(
        minutes=creation.buffer_before_minutes
    )
    buffer_after = timedelta(
        minutes=creation.buffer_after_minutes
    )

    physical_periods = [
        (
            occurrence.starts_at - buffer_before,
            occurrence.ends_at + buffer_after,
        )
        for occurrence in occurrences
    ]

    validate_physical_periods_do_not_overlap(physical_periods)

    if await has_active_occupancy_conflict(
        session,
        tenant_id=context.tenant_id,
        resource_id=creation.resource_id,
        periods=physical_periods,
    ):
        raise BookingSeriesConflict(
            "Booking series conflicts with active resource occupancy."
        )

    priced_occurrences: list[
        tuple[datetime, datetime, dict[str, object]]
    ] = []

    for occurrence in occurrences:
        pricing_snapshot = await pricing_snapshot_producer.produce(
            PricingSnapshotRequest(
                tenant_id=context.tenant_id,
                unit_id=creation.unit_id,
                resource_id=creation.resource_id,
                resource_category_id=creation.resource_category_id,
                professional_id=creation.professional_id,
                starts_at=occurrence.starts_at,
                ends_at=occurrence.ends_at,
            )
        )

        if not pricing_snapshot:
            raise InvalidBookingSeries(
                "Pricing snapshot must be a non-empty object."
            )

        priced_occurrences.append(
            (
                occurrence.starts_at,
                occurrence.ends_at,
                pricing_snapshot,
            )
        )

    first_occurrence = occurrences[0]
    last_occurrence = max(
        occurrences,
        key=lambda occurrence: occurrence.ends_at,
    )

    return await persist_create_booking_series(
        session,
        tenant_id=context.tenant_id,
        unit_id=creation.unit_id,
        resource_id=creation.resource_id,
        professional_id=creation.professional_id,
        rrule=rrule.strip(),
        timezone=timezone.strip(),
        starts_at=first_occurrence.starts_at,
        ends_at=last_occurrence.ends_at,
        buffer_before_minutes=creation.buffer_before_minutes,
        buffer_after_minutes=creation.buffer_after_minutes,
        notes=notes,
        occurrences=priced_occurrences,
    )


async def confirm_booking(
    session: AsyncSession,
    *,
    context: TenantContext,
    booking_id: UUID,
) -> Booking:
    """Confirm one PENDING booking and acquire canonical occupancy."""

    require_permission(context, Permission.OPERATIONS)

    booking = await repository_get_booking(
        session,
        tenant_id=context.tenant_id,
        booking_id=booking_id,
    )

    if booking is None:
        raise BookingNotFound("Booking not found.")

    if booking.status is not BookingStatus.PENDING:
        raise BookingConflict(
            "Only a PENDING booking can be confirmed."
        )

    confirmed = await persist_confirm_booking(
        session,
        tenant_id=context.tenant_id,
        booking_id=booking_id,
    )

    if confirmed is None:
        raise BookingConflict(
            "Booking could not be confirmed in its current state."
        )

    return confirmed


async def cancel_booking(
    session: AsyncSession,
    *,
    context: TenantContext,
    booking_id: UUID,
    reason: str | None = None,
) -> Booking:
    """Cancel one PENDING or CONFIRMED booking and audit the operation."""

    require_permission(context, Permission.OPERATIONS)

    booking = await repository_get_booking(
        session,
        tenant_id=context.tenant_id,
        booking_id=booking_id,
    )

    if booking is None:
        raise BookingNotFound("Booking not found.")

    if booking.status not in {
        BookingStatus.PENDING,
        BookingStatus.CONFIRMED,
    }:
        raise BookingConflict(
            "Only a PENDING or CONFIRMED booking can be cancelled."
        )

    cancelled = await persist_cancel_booking(
        session,
        tenant_id=context.tenant_id,
        booking_id=booking_id,
    )

    if cancelled is None:
        raise BookingConflict(
            "Booking could not be cancelled in its current state."
        )

    metadata: dict[str, str] = {}

    if reason is not None:
        normalized_reason = reason.strip()

        if normalized_reason:
            metadata["reason"] = normalized_reason

    await create_audit_log(
        session,
        tenant_id=context.tenant_id,
        actor_external_user_id=context.external_user_id,
        action="BOOKING_CANCELLED",
        entity_type="BOOKING",
        entity_id=cancelled.id,
        metadata=metadata,
    )

    return cancelled


async def extend_booking(
    session: AsyncSession,
    *,
    context: TenantContext,
    booking_id: UUID,
    ends_at: datetime,
) -> Booking:
    """Extend one CONFIRMED booking while preserving its snapshot and buffers."""

    require_permission(context, Permission.OPERATIONS)

    booking = await repository_get_booking(
        session,
        tenant_id=context.tenant_id,
        booking_id=booking_id,
    )

    if booking is None:
        raise BookingNotFound("Booking not found.")

    if booking.status is not BookingStatus.CONFIRMED:
        raise BookingConflict(
            "Only a CONFIRMED booking can be extended."
        )

    validate_booking_period(booking.starts_at, ends_at)

    if ends_at <= booking.ends_at:
        raise InvalidBooking(
            "Extension ends_at must be after the current ends_at."
        )

    extended = await persist_extend_booking(
        session,
        tenant_id=context.tenant_id,
        booking_id=booking_id,
        ends_at=ends_at,
    )

    if extended is None:
        raise BookingConflict(
            "Booking could not be extended in its current state."
        )

    return extended





async def cancel_booking_series(
    session: AsyncSession,
    *,
    context: TenantContext,
    series_id: UUID,
) -> BookingSeries:
    """Cancel one series and its future cancellable booking occurrences."""

    require_permission(context, Permission.OPERATIONS)

    series = await repository_get_booking_series(
        session,
        tenant_id=context.tenant_id,
        series_id=series_id,
    )

    if series is None:
        raise BookingSeriesNotFound("Booking series not found.")

    if series.cancelled_at is not None:
        raise BookingSeriesConflict(
            "Booking series is already cancelled."
        )

    cancelled = await persist_cancel_booking_series(
        session,
        tenant_id=context.tenant_id,
        series_id=series_id,
    )

    if cancelled is None:
        raise BookingSeriesConflict(
            "Booking series could not be cancelled in its current state."
        )

    return cancelled
