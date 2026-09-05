"""HTTP routes for BCOS availability."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.availability.domain import (
    Availability,
    InvalidAvailabilityInterval,
)
from bcos_api.availability.schemas import (
    AvailabilityItem,
    AvailabilityResponse,
)
from bcos_api.availability.service import (
    AvailabilityCategoryNotFound,
    AvailabilityResourceNotFound,
    AvailabilityUnitNotFound,
    get_tenant_availability,
)
from bcos_api.db.session import get_async_session
from bcos_api.openapi_responses import error_responses
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context

router = APIRouter(
    prefix="/api/v1/availability",
    tags=["Availability"],
)

SessionDependency = Annotated[
    AsyncSession,
    Depends(get_async_session),
]
TenantContextDependency = Annotated[
    TenantContext,
    Depends(get_tenant_context),
]


def _to_item(availability: Availability) -> AvailabilityItem:
    return AvailabilityItem(
        resource_id=availability.resource_id,
        available=availability.available,
        reason=availability.reason,
    )


@router.get(
    "",
    summary="Consultar disponibilidade",
    operation_id="getAvailability",
    description=(
        "Consulta preventiva para UX.\n"
        "Não reserva o recurso; ResourceOccupancy no PostgreSQL "
        "é a autoridade definitiva."
    ),
    response_model=AvailabilityResponse,
    response_description="Disponibilidade calculada",
    responses=error_responses(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def get_availability(
    session: SessionDependency,
    context: TenantContextDependency,
    unit_id: Annotated[UUID, Query()],
    starts_at: Annotated[datetime, Query()],
    ends_at: Annotated[datetime, Query()],
    resource_id: Annotated[UUID | None, Query()] = None,
    category_id: Annotated[UUID | None, Query()] = None,
) -> AvailabilityResponse:
    try:
        resources = await get_tenant_availability(
            session,
            context=context,
            unit_id=unit_id,
            starts_at=starts_at,
            ends_at=ends_at,
            resource_id=resource_id,
            category_id=category_id,
        )
    except (
        InvalidAvailabilityInterval,
        AvailabilityUnitNotFound,
        AvailabilityResourceNotFound,
        AvailabilityCategoryNotFound,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return AvailabilityResponse(
        starts_at=starts_at,
        ends_at=ends_at,
        resources=[_to_item(resource) for resource in resources],
    )



