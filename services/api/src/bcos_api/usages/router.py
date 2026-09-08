"""HTTP routes for BCOS Usage."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.db.session import get_async_session
from bcos_api.openapi_responses import error_responses
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.usages.domain import InvalidUsage
from bcos_api.usages.domain import Usage as DomainUsage
from bcos_api.usages.schemas import (
    CheckInRequest,
    CheckOutRequest,
)
from bcos_api.usages.schemas import (
    Usage as UsageResponse,
)
from bcos_api.usages.schemas import UsageStatus as PublicUsageStatus
from bcos_api.usages.service import (
    UsageConflict,
    UsageNotFound,
)
from bcos_api.usages.service import (
    check_in as service_check_in,
)
from bcos_api.usages.service import (
    check_out as service_check_out,
)

router = APIRouter(prefix="/api/v1", tags=["Usage"])

SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
TenantContextDependency = Annotated[
    TenantContext,
    Depends(get_tenant_context),
]


def _usage_to_response(usage: DomainUsage) -> UsageResponse:
    """Map the Usage domain model to the frozen public API schema."""

    return UsageResponse(
        id=usage.id,
        booking_id=usage.booking_id,
        resource_id=usage.resource_id,
        professional_id=usage.professional_id,
        status=PublicUsageStatus(usage.status.value),
        checked_in_at=usage.checked_in_at,
        checked_out_at=usage.checked_out_at,
    )


@router.post(
    "/usages/check-in",
    operation_id="checkIn",
    response_model=UsageResponse,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
    ),
)
async def check_in(
    payload: CheckInRequest,
    session: SessionDependency,
    context: TenantContextDependency,
) -> UsageResponse:
    """Create or start Usage corresponding to one confirmed Booking."""

    try:
        usage = await service_check_in(
            session,
            context=context,
            booking_id=payload.booking_id,
            checked_in_at=payload.checked_in_at,
        )
        await session.commit()
    except UsageNotFound as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (UsageConflict, InvalidUsage, IntegrityError) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Booking is not eligible for check-in.",
        ) from exc
    except Exception:
        await session.rollback()
        raise

    return _usage_to_response(usage)


@router.post(
    "/usages/{usage_id}/check-out",
    operation_id="checkOut",
    response_model=UsageResponse,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
    ),
)
async def check_out(
    usage_id: UUID,
    session: SessionDependency,
    context: TenantContextDependency,
    payload: Annotated[CheckOutRequest | None, Body()] = None,
) -> UsageResponse:
    """Complete Usage and persist USAGE_COMPLETED in the Outbox."""

    try:
        usage = await service_check_out(
            session,
            context=context,
            usage_id=usage_id,
            checked_out_at=(
                payload.checked_out_at if payload is not None else None
            ),
        )
        await session.commit()
    except UsageNotFound as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (UsageConflict, InvalidUsage, IntegrityError) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usage is not eligible for check-out.",
        ) from exc
    except Exception:
        await session.rollback()
        raise

    return _usage_to_response(usage)
