"""Own-scope read routes for the BCOS Professional Portal."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.billing import repository as billing_repository
from bcos_api.billing.schemas import InvoiceSummary
from bcos_api.bookings import repository as bookings_repository
from bcos_api.bookings.schemas import Booking as BookingResponse
from bcos_api.bookings.schemas import BookingStatus as PublicBookingStatus
from bcos_api.db.session import get_async_session
from bcos_api.openapi_responses import error_responses
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.tenancy.professional_scope import (
    ProfessionalScopeDenied,
    resolve_professional_scope,
)

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
