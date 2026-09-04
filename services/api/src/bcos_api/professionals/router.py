"""HTTP routes for BCOS professionals."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.db.session import get_async_session
from bcos_api.openapi_responses import error_responses
from bcos_api.professionals.domain import InvalidProfessional
from bcos_api.professionals.schemas import (
    Professional as ProfessionalResponse,
)
from bcos_api.professionals.schemas import (
    ProfessionalCreate as ProfessionalCreateRequest,
)
from bcos_api.professionals.schemas import (
    ProfessionalUpdate as ProfessionalUpdateRequest,
)
from bcos_api.professionals.service import (
    ProfessionalNotFound,
    create_tenant_professional,
    get_tenant_professional,
    list_tenant_professionals,
    update_tenant_professional,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context

router = APIRouter(
    prefix="/api/v1/professionals",
    tags=["Professionals"],
)

SessionDependency = Annotated[
    AsyncSession,
    Depends(get_async_session),
]
TenantContextDependency = Annotated[
    TenantContext,
    Depends(get_tenant_context),
]


def _to_response(professional: object) -> ProfessionalResponse:
    """Map a professional domain object to its public representation."""

    from bcos_api.professionals.domain import Professional

    if not isinstance(professional, Professional):
        raise TypeError("Expected Professional domain object.")

    return ProfessionalResponse(
        id=professional.id,
        external_user_id=professional.external_user_id,
        name=professional.name,
        email=professional.email,
        phone=professional.phone,
        status=professional.status,
    )


@router.get(
    "",
    response_model=list[ProfessionalResponse],
)
async def list_professionals(
    session: SessionDependency,
    context: TenantContextDependency,
) -> list[ProfessionalResponse]:
    """List professionals visible inside the authorized tenant."""

    professionals = await list_tenant_professionals(
        session,
        context=context,
    )

    return [
        _to_response(professional)
        for professional in professionals
    ]


@router.post(
    "",
    response_model=ProfessionalResponse,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_409_CONFLICT,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def create_professional(
    payload: ProfessionalCreateRequest,
    session: SessionDependency,
    context: TenantContextDependency,
) -> ProfessionalResponse:
    """Create one professional inside the authorized tenant."""

    try:
        professional = await create_tenant_professional(
            session,
            context=context,
            external_user_id=payload.external_user_id,
            name=payload.name,
            email=str(payload.email) if payload.email is not None else None,
            phone=payload.phone,
        )
        await session.commit()
    except InvalidProfessional as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Professional conflicts with an existing record.",
        ) from exc

    return _to_response(professional)


@router.get(
    "/{professional_id}",
    response_model=ProfessionalResponse,
    responses=error_responses(
        status.HTTP_404_NOT_FOUND,
    ),
)
async def get_professional(
    professional_id: UUID,
    session: SessionDependency,
    context: TenantContextDependency,
) -> ProfessionalResponse:
    """Get one professional inside the authorized tenant."""

    try:
        professional = await get_tenant_professional(
            session,
            context=context,
            professional_id=professional_id,
        )
    except ProfessionalNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _to_response(professional)


@router.patch(
    "/{professional_id}",
    response_model=ProfessionalResponse,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    ),
)
async def update_professional(
    professional_id: UUID,
    payload: ProfessionalUpdateRequest,
    session: SessionDependency,
    context: TenantContextDependency,
) -> ProfessionalResponse:
    """Update one professional inside the authorized tenant."""

    try:
        current = await get_tenant_professional(
            session,
            context=context,
            professional_id=professional_id,
        )

        external_user_id = (
            payload.external_user_id
            if "external_user_id" in payload.model_fields_set
            else current.external_user_id
        )
        name = (
            payload.name
            if "name" in payload.model_fields_set
            else current.name
        )
        email = (
            str(payload.email)
            if "email" in payload.model_fields_set
            and payload.email is not None
            else (
                None
                if "email" in payload.model_fields_set
                else current.email
            )
        )
        phone = (
            payload.phone
            if "phone" in payload.model_fields_set
            else current.phone
        )
        professional_status = (
            payload.status
            if "status" in payload.model_fields_set
            else current.status
        )

        if name is None or professional_status is None:
            raise InvalidProfessional(
                "Professional name and status must not be null."
            )

        professional = await update_tenant_professional(
            session,
            context=context,
            professional_id=professional_id,
            external_user_id=external_user_id,
            name=name,
            email=email,
            phone=phone,
            status=professional_status,
        )
        await session.commit()
    except ProfessionalNotFound as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidProfessional as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Professional conflicts with an existing record.",
        ) from exc

    return _to_response(professional)
