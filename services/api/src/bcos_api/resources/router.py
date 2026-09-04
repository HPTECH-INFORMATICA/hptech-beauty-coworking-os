"""HTTP routes for BCOS resources."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.db.session import get_async_session
from bcos_api.openapi_responses import error_responses
from bcos_api.resources.domain import InvalidResource, Resource
from bcos_api.resources.schemas import (
    Resource as ResourceResponse,
)
from bcos_api.resources.schemas import (
    ResourceCreate as ResourceCreateRequest,
)
from bcos_api.resources.schemas import (
    ResourceOperationalStatus,
)
from bcos_api.resources.schemas import (
    ResourceUpdate as ResourceUpdateRequest,
)
from bcos_api.resources.service import (
    ResourceCategoryNotFound,
    ResourceNotFound,
    ResourceUnitNotFound,
    create_tenant_resource,
    get_tenant_resource,
    list_tenant_resources,
    update_tenant_resource,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context

router = APIRouter(
    prefix="/api/v1/resources",
    tags=["Resources"],
)

SessionDependency = Annotated[
    AsyncSession,
    Depends(get_async_session),
]
TenantContextDependency = Annotated[
    TenantContext,
    Depends(get_tenant_context),
]


def _to_response(resource: Resource) -> ResourceResponse:
    return ResourceResponse(
        id=resource.id,
        unit_id=resource.unit_id,
        category_id=resource.category_id,
        name=resource.name,
        operational_status=ResourceOperationalStatus(resource.operational_status.value),
        buffer_before_minutes=resource.buffer_before_minutes,
        buffer_after_minutes=resource.buffer_after_minutes,
        active=resource.active,
    )


@router.get("", response_model=list[ResourceResponse])
async def list_resources(
    session: SessionDependency,
    context: TenantContextDependency,
    unit_id: Annotated[UUID | None, Query()] = None,
    category_id: Annotated[UUID | None, Query()] = None,
) -> list[ResourceResponse]:
    resources = await list_tenant_resources(
        session,
        context=context,
        unit_id=unit_id,
        category_id=category_id,
    )

    return [_to_response(resource) for resource in resources]


@router.post(
    "",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_409_CONFLICT,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def create_resource(
    payload: ResourceCreateRequest,
    session: SessionDependency,
    context: TenantContextDependency,
) -> ResourceResponse:
    try:
        resource = await create_tenant_resource(
            session,
            context=context,
            unit_id=payload.unit_id,
            category_id=payload.category_id,
            name=payload.name,
            buffer_before_minutes=payload.buffer_before_minutes,
            buffer_after_minutes=payload.buffer_after_minutes,
            active=payload.active,
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="unit_id and category_id must be valid UUIDs.",
        ) from exc
    except (InvalidResource, ResourceUnitNotFound, ResourceCategoryNotFound) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resource conflicts with an existing record.",
        ) from exc

    return _to_response(resource)


@router.get(
    "/{resource_id}",
    response_model=ResourceResponse,
    responses=error_responses(
        status.HTTP_404_NOT_FOUND,
    ),
)
async def get_resource(
    resource_id: UUID,
    session: SessionDependency,
    context: TenantContextDependency,
) -> ResourceResponse:
    try:
        resource = await get_tenant_resource(
            session,
            context=context,
            resource_id=resource_id,
        )
    except ResourceNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _to_response(resource)


@router.patch(
    "/{resource_id}",
    response_model=ResourceResponse,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    ),
)
async def update_resource(
    resource_id: UUID,
    payload: ResourceUpdateRequest,
    session: SessionDependency,
    context: TenantContextDependency,
) -> ResourceResponse:
    try:
        current = await get_tenant_resource(
            session,
            context=context,
            resource_id=resource_id,
        )

        resource = await update_tenant_resource(
            session,
            context=context,
            resource_id=resource_id,
            unit_id=current.unit_id,
            category_id=current.category_id,
            name=payload.resolve_name(current.name),
            operational_status=payload.resolve_operational_status(
                current.operational_status
            ),
            buffer_before_minutes=payload.resolve_buffer_before_minutes(
                current.buffer_before_minutes
            ),
            buffer_after_minutes=payload.resolve_buffer_after_minutes(
                current.buffer_after_minutes
            ),
            active=payload.resolve_active(current.active),
        )
        await session.commit()
    except ResourceNotFound as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidResource as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resource conflicts with an existing record.",
        ) from exc

    return _to_response(resource)

