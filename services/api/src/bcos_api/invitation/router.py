"""Authenticated first-access invitation acceptance."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.admin.schemas import MembershipResponse
from bcos_api.audit.repository import create_audit_log
from bcos_api.auth.dependencies import get_authenticated_identity
from bcos_api.auth.identity import AuthenticatedIdentity
from bcos_api.db.session import get_async_session
from bcos_api.invitation.repository import (
    accept_invited_membership,
    list_pending_invitations,
)
from bcos_api.tenancy.membership import MembershipRole

router = APIRouter(prefix="/api/v1/invitations", tags=["Invitations"])
SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
IdentityDependency = Annotated[AuthenticatedIdentity, Depends(get_authenticated_identity)]


@router.get("", response_model=list[MembershipResponse])
async def list_pending_invitations_endpoint(
    session: SessionDependency,
    identity: IdentityDependency,
) -> list[MembershipResponse]:
    memberships = await list_pending_invitations(
        session,
        external_user_id=identity.external_user_id,
    )
    return [MembershipResponse.model_validate(item) for item in memberships]


@router.post("/{membership_id}/accept", response_model=MembershipResponse)
async def accept_invitation_endpoint(
    membership_id: UUID,
    session: SessionDependency,
    identity: IdentityDependency,
) -> MembershipResponse:
    membership = await accept_invited_membership(
        session,
        membership_id=membership_id,
        external_user_id=identity.external_user_id,
    )
    if membership is None:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Pending invitation not found.")
    await create_audit_log(
        session,
        tenant_id=membership.tenant_id,
        actor_external_user_id=identity.external_user_id,
        action="TENANT_MEMBERSHIP_ACCEPTED",
        entity_type="tenant_membership",
        entity_id=membership.id,
        metadata={"role": membership.role.value, "status": membership.status.value},
    )
    await session.commit()
    return MembershipResponse.model_validate(membership)


class TeamInvitationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    tenant_name: str
    display_name: str
    email: str
    role: MembershipRole
    status: str
    expires_at: str


async def _authenticated_email(session: AsyncSession, external_user_id: str) -> str:
    result=await session.execute(text('SELECT email FROM neon_auth."user" WHERE id::text=:external_user_id LIMIT 1'), {"external_user_id":external_user_id})
    row=result.mappings().one_or_none()
    email=str(row["email"]).strip().lower() if row and row["email"] else ""
    if not email:
        raise HTTPException(status_code=409, detail="AUTHENTICATED_EMAIL_REQUIRED")
    return email


@router.get("/team", response_model=list[TeamInvitationResponse])
async def list_team_invitations_endpoint(session: SessionDependency, identity: IdentityDependency) -> list[TeamInvitationResponse]:
    email=await _authenticated_email(session, identity.external_user_id)
    result=await session.execute(text("""SELECT i.id,i.tenant_id,t.name AS tenant_name,i.display_name,i.email,i.role::text AS role,i.status,i.expires_at FROM tenant_user_invitations i JOIN tenants t ON t.id=i.tenant_id WHERE lower(i.email)=:email AND i.status='PENDING' AND i.expires_at>now() AND i.deleted_at IS NULL ORDER BY i.created_at ASC"""), {"email":email})
    return [TeamInvitationResponse(**dict(row), expires_at=row["expires_at"].isoformat()) for row in result.mappings().all()]


@router.post("/team/{invitation_id}/accept", response_model=MembershipResponse)
async def accept_team_invitation_endpoint(invitation_id: UUID, session: SessionDependency, identity: IdentityDependency) -> MembershipResponse:
    email=await _authenticated_email(session, identity.external_user_id)
    result=await session.execute(text("""SELECT i.id,i.tenant_id,i.display_name,i.email,i.role::text AS role FROM tenant_user_invitations i JOIN tenants t ON t.id=i.tenant_id WHERE i.id=:id AND lower(i.email)=:email AND i.status='PENDING' AND i.expires_at>now() AND i.deleted_at IS NULL AND t.status='ACTIVE' FOR UPDATE OF i"""), {"id":invitation_id,"email":email})
    row=result.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Pending team invitation not found.")
    try:
        inserted=await session.execute(text("""INSERT INTO tenant_memberships (tenant_id,external_user_id,role,status,display_name,email) VALUES (:tenant_id,:external_user_id,CAST(:role AS membership_role),'ACTIVE',:display_name,:email) RETURNING id,tenant_id,external_user_id,role::text AS role,status::text AS status,display_name,email"""), {"tenant_id":row["tenant_id"],"external_user_id":identity.external_user_id,"role":row["role"],"display_name":row["display_name"],"email":email})
        membership=dict(inserted.mappings().one())
        await session.execute(text("""UPDATE tenant_user_invitations SET status='ACCEPTED',accepted_at=now(),updated_at=now() WHERE id=:id"""), {"id":invitation_id})
        await create_audit_log(session,tenant_id=row["tenant_id"],actor_external_user_id=identity.external_user_id,action="TENANT_USER_INVITATION_ACCEPTED",entity_type="tenant_user_invitation",entity_id=invitation_id,metadata={"email":email,"role":row["role"]})
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409,detail="Identity already has access to this tenant.") from exc
    return MembershipResponse.model_validate(membership)
