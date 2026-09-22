"""Authenticated first-access invitation acceptance."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.audit.repository import create_audit_log
from bcos_api.auth.dependencies import get_authenticated_identity
from bcos_api.auth.identity import AuthenticatedIdentity
from bcos_api.db.session import get_async_session
from bcos_api.invitation.repository import accept_invited_membership
from bcos_api.tenancy.membership import TenantMembership
from bcos_api.admin.schemas import MembershipResponse

router = APIRouter(prefix="/api/v1/invitations", tags=["Invitations"])
SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
IdentityDependency = Annotated[AuthenticatedIdentity, Depends(get_authenticated_identity)]


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
