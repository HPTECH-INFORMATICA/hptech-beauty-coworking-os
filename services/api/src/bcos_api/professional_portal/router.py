"""Own-scope read routes for the BCOS Professional Portal."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.availability.domain import InvalidAvailabilityInterval
from bcos_api.availability.repository import list_resource_availability
from bcos_api.billing import repository as billing_repository
from bcos_api.billing.schemas import InvoiceSummary
from bcos_api.bookings import repository as bookings_repository
from bcos_api.bookings.domain import InvalidBooking
from bcos_api.bookings.pricing import PricingSnapshotRequest, PricingSnapshotUnavailable
from bcos_api.bookings.schemas import Booking as BookingResponse
from bcos_api.bookings.schemas import BookingStatus as PublicBookingStatus
from bcos_api.bookings.service import BookingConflict, create_professional_booking
from bcos_api.db.session import get_async_session
from bcos_api.openapi_responses import error_responses
from bcos_api.pricing.snapshot import DatabasePricingSnapshotProducer
from bcos_api.professional_portal.schemas import (
    ProfessionalBookingCreate,
    ProfessionalCommercialAvailability,
    ProfessionalCommercialOption,
)
from bcos_api.resources.repository import list_resources
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.tenancy.professional_scope import (
    ProfessionalScopeDenied,
    resolve_professional_scope,
)
from bcos_api.units.repository import get_unit

router = APIRouter(prefix="/api/v1/professional/me", tags=["Professional Portal"])

SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
TenantContextDependency = Annotated[TenantContext, Depends(get_tenant_context)]


def _booking_response(booking) -> BookingResponse:
    return BookingResponse(
        id=booking.id,
        unit_id=booking.unit_id,
        resource_id=booking.resource_id,
        professional_id=booking.professional_id,
        series_id=booking.series_id,
        status=PublicBookingStatus(booking.status.value),
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        buffer_before_minutes=booking.buffer_before_minutes,
        buffer_after_minutes=booking.buffer_after_minutes,
        pricing_snapshot=booking.pricing_snapshot,
    )


async def _own_professional_id(
    session: AsyncSession,
    context: TenantContext,
):
    try:
        scope = await resolve_professional_scope(session, context=context)
    except ProfessionalScopeDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return scope.professional_id


@router.get(
    "/bookings",
    response_model=list[BookingResponse],
    operation_id="listMyBookings",
    responses=error_responses(status.HTTP_403_FORBIDDEN),
)
async def list_my_bookings(
    session: SessionDependency,
    context: TenantContextDependency,
) -> list[BookingResponse]:
    """List only bookings owned by the authenticated Professional."""

    professional_id = await _own_professional_id(session, context)
    bookings = await bookings_repository.list_bookings(
        session,
        tenant_id=context.tenant_id,
        professional_id=professional_id,
    )
    return [_booking_response(booking) for booking in bookings]


@router.get(
    "/invoices",
    response_model=list[InvoiceSummary],
    operation_id="listMyInvoices",
    responses=error_responses(status.HTTP_403_FORBIDDEN),
)
async def list_my_invoices(
    session: SessionDependency,
    context: TenantContextDependency,
) -> list[InvoiceSummary]:
    """List only invoices owned by the authenticated Professional."""

    professional_id = await _own_professional_id(session, context)
    rows = await billing_repository.list_invoices(
        session,
        tenant_id=context.tenant_id,
        professional_id=professional_id,
        status=None,
        limit=100,
        offset=0,
    )
    return [InvoiceSummary(**dict(row)) for row in rows]


@router.get(
    "/commercial-availability",
    response_model=ProfessionalCommercialAvailability,
    operation_id="getMyCommercialAvailability",
    responses=error_responses(status.HTTP_403_FORBIDDEN, status.HTTP_422_UNPROCESSABLE_CONTENT),
)
async def get_my_commercial_availability(
    session: SessionDependency,
    context: TenantContextDependency,
    unit_id: Annotated[UUID, Query()],
    starts_at: Annotated[datetime, Query()],
    ends_at: Annotated[datetime, Query()],
    category_id: Annotated[UUID | None, Query()] = None,
) -> ProfessionalCommercialAvailability:
    """Return own-scope availability plus the trusted Pricing snapshot."""

    professional_id = await _own_professional_id(session, context)
    unit = await get_unit(session, tenant_id=context.tenant_id, unit_id=unit_id)
    if unit is None or not unit.active:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unit is not available.")
    try:
        availability = await list_resource_availability(
            session,
            tenant_id=context.tenant_id,
            unit_id=unit_id,
            starts_at=starts_at,
            ends_at=ends_at,
            category_id=category_id,
        )
    except InvalidAvailabilityInterval as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    resources = await list_resources(session, tenant_id=context.tenant_id, unit_id=unit_id, category_id=category_id)
    resource_by_id = {resource.id: resource for resource in resources if resource.active}
    producer = DatabasePricingSnapshotProducer(session)
    options: list[ProfessionalCommercialOption] = []
    for item in availability:
        resource = resource_by_id.get(item.resource_id)
        if resource is None:
            continue
        snapshot = None
        if item.available:
            try:
                snapshot = await producer.produce(PricingSnapshotRequest(
                    tenant_id=context.tenant_id,
                    unit_id=unit_id,
                    resource_id=resource.id,
                    resource_category_id=resource.category_id,
                    professional_id=professional_id,
                    starts_at=starts_at,
                    ends_at=ends_at,
                ))
            except PricingSnapshotUnavailable:
                snapshot = None
        options.append(ProfessionalCommercialOption(
            resource_id=resource.id,
            resource_name=resource.name,
            resource_category_id=resource.category_id,
            available=item.available and snapshot is not None,
            unavailable_reason=item.reason if not item.available else (None if snapshot is not None else "Pricing is not configured for this period."),
            pricing_snapshot=snapshot,
            price_amount=(
                snapshot["pricing_rule"]["rule_definition"]["base_price_amount"]
                if snapshot is not None
                else None
            ),
            price_currency=(
                snapshot["pricing_rule"]["currency"]
                if snapshot is not None
                else None
            ),
            price_modality=(
                snapshot["pricing_rule"]["rule_definition"]["modality"]
                if snapshot is not None
                else None
            ),
        ))
    return ProfessionalCommercialAvailability(unit_id=unit_id, starts_at=starts_at, ends_at=ends_at, resources=options)


@router.post(
    "/bookings",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createMyBooking",
    responses=error_responses(status.HTTP_403_FORBIDDEN, status.HTTP_409_CONFLICT, status.HTTP_422_UNPROCESSABLE_CONTENT),
)
async def create_my_booking(
    payload: ProfessionalBookingCreate,
    session: SessionDependency,
    context: TenantContextDependency,
) -> BookingResponse:
    """Create a PENDING booking for the authenticated professional only."""

    professional_id = await _own_professional_id(session, context)
    try:
        booking = await create_professional_booking(
            session,
            context=context,
            unit_id=payload.unit_id,
            resource_id=payload.resource_id,
            professional_id=professional_id,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            notes=payload.notes,
            pricing_snapshot_producer=DatabasePricingSnapshotProducer(session),
        )
        await session.commit()
    except InvalidBooking as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except (BookingConflict, PricingSnapshotUnavailable) as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _booking_response(booking)
