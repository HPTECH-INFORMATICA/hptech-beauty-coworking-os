"""HTTP routes for BCOS bookings."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.bookings.domain import (
    Booking as DomainBooking,
)
from bcos_api.bookings.domain import (
    BookingStatus as DomainBookingStatus,
)
from bcos_api.bookings.domain import InvalidBooking
from bcos_api.bookings.pricing import (
    PricingSnapshotProducer,
    PricingSnapshotUnavailable,
    UnconfiguredPricingSnapshotProducer,
)
from bcos_api.bookings.schemas import (
    Booking as BookingResponse,
)
from bcos_api.bookings.schemas import (
    BookingCancelRequest,
    BookingCreate,
    BookingExtendRequest,
    BookingSeriesCreate,
    BookingSeriesResult,
)
from bcos_api.bookings.schemas import (
    BookingSeries as BookingSeriesResponse,
)
from bcos_api.bookings.schemas import (
    BookingStatus as PublicBookingStatus,
)
from bcos_api.bookings.series_domain import (
    BookingSeries as DomainBookingSeries,
)
from bcos_api.bookings.series_domain import InvalidBookingSeries
from bcos_api.bookings.service import (
    BookingConflict,
    BookingNotFound,
    BookingSeriesConflict,
    BookingSeriesNotFound,
)
from bcos_api.bookings.service import (
    cancel_booking as service_cancel_booking,
)
from bcos_api.bookings.service import (
    cancel_booking_series as service_cancel_booking_series,
)
from bcos_api.bookings.service import (
    confirm_booking as service_confirm_booking,
)
from bcos_api.bookings.service import (
    create_booking as service_create_booking,
)
from bcos_api.bookings.service import (
    create_booking_series as service_create_booking_series,
)
from bcos_api.bookings.service import (
    extend_booking as service_extend_booking,
)
from bcos_api.bookings.service import (
    get_booking as service_get_booking,
)
from bcos_api.bookings.service import (
    list_bookings as service_list_bookings,
)
from bcos_api.db.session import get_async_session
from bcos_api.openapi_responses import error_responses
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context

router = APIRouter(prefix="/api/v1", tags=["Bookings"])

SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
TenantContextDependency = Annotated[
    TenantContext,
    Depends(get_tenant_context),
]


def get_pricing_snapshot_producer() -> PricingSnapshotProducer:
    """Return the trusted pricing snapshot producer configured for BCOS."""

    return UnconfiguredPricingSnapshotProducer()


PricingSnapshotProducerDependency = Annotated[
    PricingSnapshotProducer,
    Depends(get_pricing_snapshot_producer),
]


def _booking_to_response(booking: DomainBooking) -> BookingResponse:
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


def _series_to_response(
    series: DomainBookingSeries,
) -> BookingSeriesResponse:
    return BookingSeriesResponse(
        id=series.id,
        professional_id=series.professional_id,
        rrule=series.rrule,
        timezone=series.timezone,
        starts_at=series.starts_at,
        ends_at=series.ends_at,
        cancelled_at=series.cancelled_at,
    )


@router.get(
    "/bookings",
    operation_id="listBookings",
    response_model=list[BookingResponse],
)
async def list_bookings(
    session: SessionDependency,
    context: TenantContextDependency,
    starts_from: Annotated[datetime | None, Query()] = None,
    starts_until: Annotated[datetime | None, Query()] = None,
    professional_id: Annotated[UUID | None, Query()] = None,
    resource_id: Annotated[UUID | None, Query()] = None,
    status_filter: Annotated[
        PublicBookingStatus | None,
        Query(alias="status"),
    ] = None,
) -> list[BookingResponse]:
    try:
        bookings = await service_list_bookings(
            session,
            context=context,
            starts_from=starts_from,
            starts_until=starts_until,
            professional_id=professional_id,
            resource_id=resource_id,
            status=(
                DomainBookingStatus(status_filter.value)
                if status_filter is not None
                else None
            ),
        )
    except InvalidBooking as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return [_booking_to_response(booking) for booking in bookings]


@router.post(
    "/bookings",
    operation_id="createBooking",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_409_CONFLICT,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def create_booking(
    payload: BookingCreate,
    session: SessionDependency,
    context: TenantContextDependency,
    pricing_snapshot_producer: PricingSnapshotProducerDependency,
) -> BookingResponse:
    try:
        booking = await service_create_booking(
            session,
            context=context,
            unit_id=payload.unit_id,
            resource_id=payload.resource_id,
            professional_id=payload.professional_id,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            notes=payload.notes,
            pricing_snapshot_producer=pricing_snapshot_producer,
        )
        await session.commit()
    except InvalidBooking as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except (BookingConflict, PricingSnapshotUnavailable) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Booking could not be created because of a conflict.",
        ) from exc

    return _booking_to_response(booking)


@router.get(
    "/bookings/{booking_id}",
    operation_id="getBooking",
    response_model=BookingResponse,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def get_booking(
    booking_id: UUID,
    session: SessionDependency,
    context: TenantContextDependency,
) -> BookingResponse:
    try:
        booking = await service_get_booking(
            session,
            context=context,
            booking_id=booking_id,
        )
    except BookingNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _booking_to_response(booking)


@router.post(
    "/bookings/{booking_id}/confirm",
    operation_id="confirmBooking",
    response_model=BookingResponse,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
    ),
)
async def confirm_booking(
    booking_id: UUID,
    session: SessionDependency,
    context: TenantContextDependency,
) -> BookingResponse:
    try:
        booking = await service_confirm_booking(
            session,
            context=context,
            booking_id=booking_id,
        )
        await session.commit()
    except BookingNotFound as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except BookingConflict as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Booking conflicts with an active resource occupancy.",
        ) from exc

    return _booking_to_response(booking)


@router.post(
    "/bookings/{booking_id}/cancel",
    operation_id="cancelBooking",
    response_model=BookingResponse,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
    ),
)
async def cancel_booking(
    booking_id: UUID,
    session: SessionDependency,
    context: TenantContextDependency,
    payload: BookingCancelRequest | None = None,
) -> BookingResponse:
    try:
        booking = await service_cancel_booking(
            session,
            context=context,
            booking_id=booking_id,
            reason=payload.reason if payload is not None else None,
        )
        await session.commit()
    except BookingNotFound as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except BookingConflict as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return _booking_to_response(booking)


@router.post(
    "/bookings/{booking_id}/extend",
    operation_id="extendBooking",
    response_model=BookingResponse,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def extend_booking(
    booking_id: UUID,
    payload: BookingExtendRequest,
    session: SessionDependency,
    context: TenantContextDependency,
) -> BookingResponse:
    try:
        booking = await service_extend_booking(
            session,
            context=context,
            booking_id=booking_id,
            ends_at=payload.ends_at,
        )
        await session.commit()
    except BookingNotFound as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidBooking as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except BookingConflict as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Booking extension conflicts with an active occupancy.",
        ) from exc

    return _booking_to_response(booking)


@router.post(
    "/booking-series",
    operation_id="createBookingSeries",
    response_model=BookingSeriesResult,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_409_CONFLICT,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def create_booking_series(
    payload: BookingSeriesCreate,
    session: SessionDependency,
    context: TenantContextDependency,
    pricing_snapshot_producer: PricingSnapshotProducerDependency,
) -> BookingSeriesResult:
    try:
        series, bookings = await service_create_booking_series(
            session,
            context=context,
            unit_id=payload.unit_id,
            resource_id=payload.resource_id,
            professional_id=payload.professional_id,
            starts_at=payload.starts_at,
            duration_minutes=payload.duration_minutes,
            rrule=payload.rrule,
            timezone=payload.timezone,
            notes=payload.notes,
            pricing_snapshot_producer=pricing_snapshot_producer,
        )
        await session.commit()
    except (InvalidBooking, InvalidBookingSeries) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except (
        BookingConflict,
        BookingSeriesConflict,
        PricingSnapshotUnavailable,
    ) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Booking series could not be created because of a conflict.",
        ) from exc

    return BookingSeriesResult(
        series=_series_to_response(series),
        bookings=[_booking_to_response(booking) for booking in bookings],
    )


@router.post(
    "/booking-series/{series_id}/cancel",
    operation_id="cancelBookingSeries",
    response_model=BookingSeriesResponse,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    ),
)
async def cancel_booking_series(
    series_id: UUID,
    session: SessionDependency,
    context: TenantContextDependency,
) -> BookingSeriesResponse:
    try:
        series = await service_cancel_booking_series(
            session,
            context=context,
            series_id=series_id,
        )
        await session.commit()
    except BookingSeriesNotFound as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except BookingSeriesConflict:
        await session.rollback()
        raise

    return _series_to_response(series)
