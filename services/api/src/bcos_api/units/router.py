"""HTTP routes for BCOS units and reception hours."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.db.session import get_async_session
from bcos_api.openapi_responses import error_responses
from bcos_api.reception_hours.domain import InvalidReceptionHours
from bcos_api.reception_hours.schemas import ReceptionHours as ReceptionHoursResponse
from bcos_api.reception_hours.schemas import (
    ReceptionHoursInput as ReceptionHoursInputRequest,
)
from bcos_api.reception_hours.service import (
    InvalidReceptionHoursSet,
    ReceptionHoursInput,
    ReceptionHoursUnitNotFound,
    get_unit_reception_hours,
    replace_unit_reception_hours,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.units.domain import InvalidUnit, Unit
from bcos_api.units.schemas import (
    Unit as UnitResponse,
)
from bcos_api.units.schemas import (
    UnitCreate as UnitCreateRequest,
)
from bcos_api.units.schemas import (
    UnitUpdate as UnitUpdateRequest,
)
from bcos_api.units.service import (
    UnitNotFound,
    create_tenant_unit,
    get_tenant_unit,
    list_tenant_units,
    update_tenant_unit,
)

router = APIRouter(
    prefix="/api/v1/units",
    tags=["Units"],
)

SessionDependency = Annotated[
    AsyncSession,
    Depends(get_async_session),
]
TenantContextDependency = Annotated[
    TenantContext,
    Depends(get_tenant_context),
]


def _unit_response(unit: Unit) -> UnitResponse:
    """Map the internal Unit model to its public HTTP representation."""

    return UnitResponse(
        id=unit.id,
        name=unit.name,
        timezone=unit.timezone,
        active=unit.active,
        created_at=unit.created_at,
        updated_at=unit.updated_at,
    )


@router.get(
    "",
    response_model=list[UnitResponse],
    status_code=status.HTTP_200_OK,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ),
)
async def list_units_endpoint(
    session: SessionDependency,
    context: TenantContextDependency,
) -> list[UnitResponse]:
    """List units inside the authorized tenant."""

    units = await list_tenant_units(
        session,
        context=context,
    )

    return [_unit_response(unit) for unit in units]


@router.post(
    "",
    response_model=UnitResponse,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def create_unit_endpoint(
    payload: UnitCreateRequest,
    session: SessionDependency,
    context: TenantContextDependency,
) -> UnitResponse:
    """Create one unit inside the authorized tenant."""

    try:
        unit = await create_tenant_unit(
            session,
            context=context,
            name=payload.name,
            timezone=payload.timezone,
            active=payload.active,
        )
        await session.commit()
    except InvalidUnit as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _unit_response(unit)


@router.get(
    "/{unit_id}",
    response_model=UnitResponse,
    status_code=status.HTTP_200_OK,
    responses=error_responses(
        status.HTTP_404_NOT_FOUND,
    ),
)
async def get_unit_endpoint(
    unit_id: UUID,
    session: SessionDependency,
    context: TenantContextDependency,
) -> UnitResponse:
    """Get one unit inside the authorized tenant."""

    try:
        unit = await get_tenant_unit(
            session,
            context=context,
            unit_id=unit_id,
        )
    except UnitNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _unit_response(unit)


@router.patch(
    "/{unit_id}",
    response_model=UnitResponse,
    status_code=status.HTTP_200_OK,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def update_unit_endpoint(
    unit_id: UUID,
    payload: UnitUpdateRequest,
    session: SessionDependency,
    context: TenantContextDependency,
) -> UnitResponse:
    """Partially update one unit inside the authorized tenant."""

    try:
        current = await get_tenant_unit(
            session,
            context=context,
            unit_id=unit_id,
        )

        unit = await update_tenant_unit(
            session,
            context=context,
            unit_id=unit_id,
            name=payload.resolved_name(current.name),
            timezone=payload.resolved_timezone(current.timezone),
            active=payload.resolved_active(current.active),
        )
        await session.commit()
    except UnitNotFound as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidUnit as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _unit_response(unit)


@router.get(
    "/{unit_id}/reception-hours",
    response_model=list[ReceptionHoursResponse],
    status_code=status.HTTP_200_OK,
)
async def get_reception_hours_endpoint(
    unit_id: UUID,
    session: SessionDependency,
    context: TenantContextDependency,
) -> list[ReceptionHoursResponse]:
    """Get reception hours for one unit."""

    try:
        entries = await get_unit_reception_hours(
            session,
            context=context,
            unit_id=unit_id,
        )
    except ReceptionHoursUnitNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return [
        ReceptionHoursResponse(
            day_of_week=entry.day_of_week,
            opens_at=entry.opens_at,
            closes_at=entry.closes_at,
            is_closed=entry.is_closed,
        )
        for entry in entries
    ]


@router.put(
    "/{unit_id}/reception-hours",
    response_model=list[ReceptionHoursResponse],
    status_code=status.HTTP_200_OK,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def replace_reception_hours_endpoint(
    unit_id: UUID,
    payload: Annotated[
        list[ReceptionHoursInputRequest],
        Field(min_length=1, max_length=7),
    ],
    session: SessionDependency,
    context: TenantContextDependency,
) -> list[ReceptionHoursResponse]:
    """Replace the complete reception-hours set for one unit."""

    try:
        entries = await replace_unit_reception_hours(
            session,
            context=context,
            unit_id=unit_id,
            entries=[
                ReceptionHoursInput(
                    day_of_week=entry.day_of_week,
                    opens_at=entry.opens_at,
                    closes_at=entry.closes_at,
                    is_closed=entry.is_closed,
                )
                for entry in payload
            ],
        )
        await session.commit()
    except (
        InvalidReceptionHours,
        InvalidReceptionHoursSet,
    ) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ReceptionHoursUnitNotFound as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return [
        ReceptionHoursResponse(
            day_of_week=entry.day_of_week,
            opens_at=entry.opens_at,
            closes_at=entry.closes_at,
            is_closed=entry.is_closed,
        )
        for entry in entries
    ]


