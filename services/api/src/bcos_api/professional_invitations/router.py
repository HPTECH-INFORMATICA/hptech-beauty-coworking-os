"""Email-first professional access invitation routes."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.audit.repository import create_audit_log
from bcos_api.auth.dependencies import get_authenticated_identity
from bcos_api.auth.identity import AuthenticatedIdentity
from bcos_api.db.session import get_async_session
from bcos_api.professional_invitations.schemas import (
    ProfessionalAccessInvitation,
    ProfessionalAccessInvitationCreated,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.tenancy.rbac import Permission, require_permission

router = APIRouter(prefix="/api/v1/professional-invitations", tags=["Professional Invitations"])
SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
IdentityDependency = Annotated[AuthenticatedIdentity, Depends(get_authenticated_identity)]
TenantContextDependency = Annotated[TenantContext, Depends(get_tenant_context)]

async def _authenticated_email(session: AsyncSession, external_user_id: str) -> str:
    result = await session.execute(
        text('SELECT email FROM neon_auth."user" WHERE id::text = :external_user_id LIMIT 1'),
        {"external_user_id": external_user_id},
    )
    row = result.mappings().one_or_none()
    email = str(row["email"]).strip().lower() if row and row["email"] else ""
    if not email:
        raise HTTPException(status_code=409, detail="AUTHENTICATED_EMAIL_REQUIRED")
    return email

@router.post("/professionals/{professional_id}", response_model=ProfessionalAccessInvitationCreated, status_code=status.HTTP_201_CREATED)
async def create_professional_invitation(
    professional_id: UUID,
    session: SessionDependency,
    context: TenantContextDependency,
) -> ProfessionalAccessInvitationCreated:
    require_permission(context, Permission.TENANT_ADMIN)
    professional = await session.execute(
        text("""SELECT id, email FROM professionals
                WHERE id=:professional_id AND tenant_id=:tenant_id
                  AND status='ACTIVE' AND deleted_at IS NULL"""),
        {"professional_id": professional_id, "tenant_id": context.tenant_id},
    )
    row = professional.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Professional not found.")
    email = str(row["email"] or "").strip().lower()
    if not email:
        raise HTTPException(status_code=422, detail="PROFESSIONAL_EMAIL_REQUIRED")
    await session.execute(
        text("""UPDATE professional_access_invitations
                SET status='REVOKED', updated_at=now()
                WHERE tenant_id=:tenant_id AND professional_id=:professional_id
                  AND status='PENDING' AND deleted_at IS NULL"""),
        {"tenant_id": context.tenant_id, "professional_id": professional_id},
    )
    result = await session.execute(
        text("""INSERT INTO professional_access_invitations
                (tenant_id, professional_id, email, invited_by_external_user_id)
                VALUES (:tenant_id,:professional_id,:email,:actor)
                RETURNING id, professional_id, email, status, expires_at"""),
        {"tenant_id": context.tenant_id, "professional_id": professional_id, "email": email, "actor": context.external_user_id},
    )
    invitation = result.mappings().one()
    await create_audit_log(
        session, tenant_id=context.tenant_id, actor_external_user_id=context.external_user_id,
        action="PROFESSIONAL_ACCESS_INVITED", entity_type="professional_access_invitation",
        entity_id=invitation["id"], metadata={"professional_id": str(professional_id), "email": email},
    )
    await session.commit()
    return ProfessionalAccessInvitationCreated.model_validate(dict(invitation))

@router.get("", response_model=list[ProfessionalAccessInvitation])
async def list_my_professional_invitations(
    session: SessionDependency,
    identity: IdentityDependency,
) -> list[ProfessionalAccessInvitation]:
    email = await _authenticated_email(session, identity.external_user_id)
    result = await session.execute(
        text("""SELECT i.id, i.tenant_id, t.name AS tenant_name, i.professional_id,
                       p.name AS professional_name, i.email, i.status, i.expires_at
                FROM professional_access_invitations i
                JOIN tenants t ON t.id=i.tenant_id
                JOIN professionals p ON p.id=i.professional_id AND p.tenant_id=i.tenant_id
                WHERE lower(i.email)=:email AND i.status='PENDING'
                  AND i.expires_at > now() AND i.deleted_at IS NULL
                  AND p.status='ACTIVE' AND p.deleted_at IS NULL
                ORDER BY i.created_at ASC, i.id ASC"""),
        {"email": email},
    )
    return [ProfessionalAccessInvitation.model_validate(dict(row)) for row in result.mappings().all()]

@router.post("/{invitation_id}/accept", response_model=ProfessionalAccessInvitation)
async def accept_professional_invitation(
    invitation_id: UUID,
    session: SessionDependency,
    identity: IdentityDependency,
) -> ProfessionalAccessInvitation:
    email = await _authenticated_email(session, identity.external_user_id)
    invitation_result = await session.execute(
        text("""SELECT i.id, i.tenant_id, t.name AS tenant_name, i.professional_id,
                       p.name AS professional_name, i.email, i.status, i.expires_at,
                       p.external_user_id AS professional_external_user_id
                FROM professional_access_invitations i
                JOIN tenants t ON t.id=i.tenant_id
                JOIN professionals p ON p.id=i.professional_id AND p.tenant_id=i.tenant_id
                WHERE i.id=:invitation_id AND lower(i.email)=:email
                  AND i.status='PENDING' AND i.expires_at > now()
                  AND i.deleted_at IS NULL AND p.status='ACTIVE' AND p.deleted_at IS NULL
                FOR UPDATE OF i, p"""),
        {"invitation_id": invitation_id, "email": email},
    )
    row = invitation_result.mappings().one_or_none()
    if row is None:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Pending professional invitation not found.")
    bound = str(row["professional_external_user_id"] or "").strip()
    if bound and bound != identity.external_user_id:
        await session.rollback()
        raise HTTPException(status_code=409, detail="PROFESSIONAL_ALREADY_BOUND")
    existing = await session.execute(
        text("""SELECT id, role::text AS role, status::text AS status
                FROM tenant_memberships
                WHERE tenant_id=:tenant_id AND external_user_id=:external_user_id
                  AND deleted_at IS NULL LIMIT 1"""),
        {"tenant_id": row["tenant_id"], "external_user_id": identity.external_user_id},
    )
    membership = existing.mappings().one_or_none()
    if membership and membership["role"] != "PROFESSIONAL":
        await session.rollback()
        raise HTTPException(status_code=409, detail="IDENTITY_HAS_DIFFERENT_TENANT_ROLE")
    try:
        if membership is None:
            await session.execute(
                text("""INSERT INTO tenant_memberships
                        (tenant_id, external_user_id, role, status)
                        VALUES (:tenant_id,:external_user_id,'PROFESSIONAL','ACTIVE')"""),
                {"tenant_id": row["tenant_id"], "external_user_id": identity.external_user_id},
            )
        else:
            await session.execute(
                text("""UPDATE tenant_memberships SET status='ACTIVE', updated_at=now()
                        WHERE id=:membership_id"""),
                {"membership_id": membership["id"]},
            )
        await session.execute(
            text("""UPDATE professionals SET external_user_id=:external_user_id, updated_at=now()
                    WHERE id=:professional_id AND tenant_id=:tenant_id"""),
            {"external_user_id": identity.external_user_id, "professional_id": row["professional_id"], "tenant_id": row["tenant_id"]},
        )
        await session.execute(
            text("""UPDATE professional_access_invitations
                    SET status='ACCEPTED', accepted_by_external_user_id=:external_user_id,
                        accepted_at=now(), updated_at=now()
                    WHERE id=:invitation_id"""),
            {"external_user_id": identity.external_user_id, "invitation_id": invitation_id},
        )
        await create_audit_log(
            session, tenant_id=row["tenant_id"], actor_external_user_id=identity.external_user_id,
            action="PROFESSIONAL_ACCESS_ACCEPTED", entity_type="professional_access_invitation",
            entity_id=invitation_id, metadata={"professional_id": str(row["professional_id"]), "email": email},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Professional access conflicts with an existing identity binding.") from exc
    accepted = dict(row)
    accepted["status"] = "ACCEPTED"
    return ProfessionalAccessInvitation.model_validate(accepted)
