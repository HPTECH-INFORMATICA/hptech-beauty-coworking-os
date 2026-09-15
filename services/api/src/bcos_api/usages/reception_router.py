"""Reception read projections backed by canonical BCOS operational state."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.bookings.domain import InvalidBooking
from bcos_api.bookings.schemas import Booking as BookingResponse
from bcos_api.bookings.schemas import BookingStatus as PublicBookingStatus
from bcos_api.bookings.service import list_bookings
from bcos_api.db.session import get_async_session
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.tenancy.rbac import Permission, require_permission
from bcos_api.usages.repository import get_usage_by_booking
from bcos_api.usages.schemas import Usage as UsageResponse
from bcos_api.usages.schemas import UsageStatus as PublicUsageStatus

router = APIRouter(prefix="/api/v1/reception", tags=["Reception"])

SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
TenantContextDependency = Annotated[TenantContext, Depends(get_tenant_context)]


class ReceptionNow(BaseModel):
    """Frozen ReceptionNow contract: resource entries intentionally remain extensible."""

    model_config = ConfigDict(title="ReceptionNow")

    unit_id: UUID
    generated_at: datetime
    resources: list[dict[str, Any]]


class AgendaEntry(BaseModel):
    """Frozen reception agenda projection joining Booking with its optional Usage."""

    model_config = ConfigDict(title="AgendaEntry")

    booking: BookingResponse
    usage: UsageResponse | None = None


def _booking_response(booking: Any) -> BookingResponse:
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


def _usage_response(usage: Any) -> UsageResponse:
    return UsageResponse(
        id=usage.id,
        booking_id=usage.booking_id,
        resource_id=usage.resource_id,
        professional_id=usage.professional_id,
        status=PublicUsageStatus(usage.status.value),
        checked_in_at=usage.checked_in_at,
        checked_out_at=usage.checked_out_at,
    )


@router.get("/now", operation_id="getReceptionNow", response_model=ReceptionNow)
async def get_reception_now(
    session: SessionDependency,
    context: TenantContextDependency,
    unit_id: Annotated[UUID, Query()],
) -> ReceptionNow:
    """Project current physical occupancy from ResourceOccupancy, never from clock inference."""

    require_permission(context, Permission.OPERATIONS)
    result = await session.execute(
        text(
            """
            SELECT
                r.id AS resource_id,
                r.name AS resource_name,
                r.operational_status,
                ro.source_id AS booking_id,
                b.professional_id,
                b.starts_at,
                b.ends_at,
                u.id AS usage_id,
                u.status AS usage_status,
                u.checked_in_at,
                u.checked_out_at
            FROM resources AS r
            LEFT JOIN resource_occupancies AS ro
              ON ro.tenant_id = r.tenant_id
             AND ro.resource_id = r.id
             AND ro.status = 'ACTIVE'
             AND ro.period @> now()
            LEFT JOIN bookings AS b
              ON b.tenant_id = r.tenant_id
             AND ro.source_type = 'BOOKING'
             AND b.id = ro.source_id
            LEFT JOIN usages AS u
              ON u.tenant_id = r.tenant_id
             AND u.booking_id = b.id
            WHERE r.tenant_id = :tenant_id
              AND r.unit_id = :unit_id
              AND r.active = TRUE
              AND r.deleted_at IS NULL
            ORDER BY r.name ASC
            """
        ),
        {"tenant_id": context.tenant_id, "unit_id": unit_id},
    )
    resources = [dict(row) for row in result.mappings().all()]
    return ReceptionNow(
        unit_id=unit_id,
        generated_at=datetime.now(timezone.utc),
        resources=resources,
    )


@router.get("/agenda", operation_id="getReceptionAgenda", response_model=list[AgendaEntry])
async def get_reception_agenda(
    session: SessionDependency,
    context: TenantContextDependency,
    unit_id: Annotated[UUID, Query()],
    starts_at: Annotated[datetime, Query()],
    ends_at: Annotated[datetime, Query()],
) -> list[AgendaEntry]:
    """Return the operational agenda with Booking and its distinct optional Usage."""

    try:
        bookings = await list_bookings(
            session,
            context=context,
            starts_from=starts_at,
            starts_until=ends_at,
        )
    except InvalidBooking as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    entries: list[AgendaEntry] = []
    for booking in bookings:
        if booking.unit_id != unit_id:
            continue
        usage = await get_usage_by_booking(
            session,
            tenant_id=context.tenant_id,
            booking_id=booking.id,
        )
        entries.append(
            AgendaEntry(
                booking=_booking_response(booking),
                usage=_usage_response(usage) if usage is not None else None,
            )
        )
    return entries
