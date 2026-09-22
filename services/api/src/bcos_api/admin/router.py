"""Tenant administration HTTP routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.admin.domain import InvalidMembershipAdministration
from bcos_api.admin.schemas import (
    MembershipInvitationCreate,
    MembershipResponse,
    MembershipStatusUpdate,
)
from bcos_api.admin.service import (
    invite_tenant_membership,
    list_tenant_memberships,
    update_tenant_membership_status,
)
from bcos_api.db.session import get_async_session
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context

router=APIRouter(prefix="/api/v1/admin/memberships", tags=["Tenant Administration"])
SessionDependency=Annotated[AsyncSession, Depends(get_async_session)]
TenantContextDependency=Annotated[TenantContext, Depends(get_tenant_context)]


@router.get("", response_model=list[MembershipResponse])
async def list_memberships_endpoint(session: SessionDependency, context: TenantContextDependency) -> list[MembershipResponse]:
    items=await list_tenant_memberships(session, context=context)
    return [MembershipResponse.model_validate(item) for item in items]


@router.post("/invitations", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def invite_membership_endpoint(payload: MembershipInvitationCreate, session: SessionDependency, context: TenantContextDependency) -> MembershipResponse:
    try:
        item=await invite_tenant_membership(session, context=context, external_user_id=payload.external_user_id, role=payload.role)
        await session.commit()
    except (InvalidMembershipAdministration, ValueError) as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Membership already exists for this identity.") from exc
    return MembershipResponse.model_validate(item)


@router.patch("/{membership_id}/status", response_model=MembershipResponse)
async def update_membership_status_endpoint(membership_id: UUID, payload: MembershipStatusUpdate, session: SessionDependency, context: TenantContextDependency) -> MembershipResponse:
    try:
        item=await update_tenant_membership_status(session, context=context, membership_id=membership_id, status=payload.status)
        if item is None:
            raise HTTPException(status_code=404, detail="Membership not found.")
        await session.commit()
    except InvalidMembershipAdministration as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return MembershipResponse.model_validate(item)
