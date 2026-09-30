"""HTTP routes for BCOS resource categories."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.db.session import get_async_session
from bcos_api.openapi_responses import error_responses
from bcos_api.resource_categories.domain import (
    InvalidResourceCategory,
    ResourceCategory,
)
from bcos_api.resource_categories.schemas import (
    ResourceCategory as ResourceCategoryResponse,
)
from bcos_api.resource_categories.schemas import (
    ResourceCategoryCreate as ResourceCategoryCreateRequest,
)
from bcos_api.resource_categories.schemas import (
    ResourceCategoryUpdate as ResourceCategoryUpdateRequest,
)
from bcos_api.resource_categories.service import (
    ResourceCategoryDeleteConflict,
    ResourceCategoryNotFound,
    create_tenant_resource_category,
    delete_tenant_resource_category,
    list_tenant_resource_categories,
    update_tenant_resource_category,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context

router = APIRouter(
    prefix="/api/v1/resource-categories",
    tags=["Resource Categories"],
)

SessionDependency = Annotated[
    AsyncSession,
    Depends(get_async_session),
]
TenantContextDependency = Annotated[
    TenantContext,
    Depends(get_tenant_context),
]


def _to_response(
    category: ResourceCategory,
) -> ResourceCategoryResponse:
    """Map a resource category to its public representation."""

    return ResourceCategoryResponse(
        id=category.id,
        name=category.name,
        active=category.active,
    )


@router.get(
    "",
    response_model=list[ResourceCategoryResponse],
)
async def list_resource_categories(
    session: SessionDependency,
    context: TenantContextDependency,
) -> list[ResourceCategoryResponse]:
    """List resource categories inside the authorized tenant."""

    categories = await list_tenant_resource_categories(
        session,
        context=context,
    )

    return [
        _to_response(category)
        for category in categories
    ]


@router.post(
    "",
    response_model=ResourceCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_409_CONFLICT,
    ),
)
async def create_resource_category(
    payload: ResourceCategoryCreateRequest,
    session: SessionDependency,
    context: TenantContextDependency,
) -> ResourceCategoryResponse:
    """Create a resource category inside the authorized tenant."""

    try:
        category = await create_tenant_resource_category(
            session,
            context=context,
            name=payload.name,
            active=payload.active,
        )
        await session.commit()
    except InvalidResourceCategory as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resource category conflicts with an existing record.",
        ) from exc

    return _to_response(category)


@router.patch(
    "/{category_id}",
    response_model=ResourceCategoryResponse,
    responses=error_responses(status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND, status.HTTP_409_CONFLICT),
)
async def update_resource_category(
    category_id: UUID,
    payload: ResourceCategoryUpdateRequest,
    session: SessionDependency,
    context: TenantContextDependency,
) -> ResourceCategoryResponse:
    try:
        category = await update_tenant_resource_category(
            session, context=context, category_id=category_id,
            name=payload.name, active=payload.active,
        )
        await session.commit()
    except ResourceCategoryNotFound as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidResourceCategory as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resource category conflicts with an existing record.") from exc
    return _to_response(category)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND, status.HTTP_409_CONFLICT),
)
async def delete_resource_category(
    category_id: UUID,
    session: SessionDependency,
    context: TenantContextDependency,
) -> None:
    try:
        await delete_tenant_resource_category(session, context=context, category_id=category_id)
        await session.commit()
    except ResourceCategoryNotFound as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceCategoryDeleteConflict as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
