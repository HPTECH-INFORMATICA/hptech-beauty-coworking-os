"""Tenant-controlled professional self-onboarding."""
from __future__ import annotations

import hashlib
import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.audit.repository import create_audit_log
from bcos_api.db.session import get_async_session
from bcos_api.notifications.email import send_professional_access_invitation
from bcos_api.professional_onboarding.schemas import (
    ProfessionalOnboardingLink,
    ProfessionalOnboardingRequest,
    ProfessionalOnboardingSubmit,
    PublicOnboarding,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.tenancy.rbac import Permission, require_permission

router = APIRouter(prefix="/api/v1/professional-onboarding", tags=["Professional Onboarding"])
SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
TenantContextDependency = Annotated[TenantContext, Depends(get_tenant_context)]


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/links", response_model=ProfessionalOnboardingLink, status_code=status.HTTP_201_CREATED)
async def create_onboarding_link(session: SessionDependency, context: TenantContextDependency) -> ProfessionalOnboardingLink:
    require_permission(context, Permission.TENANT_ADMIN)
    token = secrets.token_urlsafe(32)
    result = await session.execute(
        text("""INSERT INTO professional_onboarding_links
                (tenant_id, token_hash, created_by_external_user_id)
                VALUES (:tenant_id,:token_hash,:actor) RETURNING id"""),
        {"tenant_id": context.tenant_id, "token_hash": _hash_token(token), "actor": context.external_user_id},
    )
    link_id = result.scalar_one()
    await create_audit_log(
        session, tenant_id=context.tenant_id, actor_external_user_id=context.external_user_id,
        action="PROFESSIONAL_ONBOARDING_LINK_CREATED", entity_type="professional_onboarding_link",
        entity_id=link_id, metadata={},
    )
    await session.commit()
    return ProfessionalOnboardingLink(id=link_id, token=token, public_path=f"/cadastro-profissional/{token}")


@router.get("/public/{token}", response_model=PublicOnboarding)
async def get_public_onboarding(token: str, session: SessionDependency) -> PublicOnboarding:
    result = await session.execute(
        text("""SELECT l.tenant_id, t.name AS tenant_name
                FROM professional_onboarding_links l JOIN tenants t ON t.id=l.tenant_id
                WHERE l.token_hash=:token_hash AND l.status='ACTIVE' AND l.deleted_at IS NULL
                  AND (l.expires_at IS NULL OR l.expires_at > now()) AND t.status='ACTIVE' LIMIT 1"""),
        {"token_hash": _hash_token(token)},
    )
    link = result.mappings().one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Onboarding link not found.")
    documents = await session.execute(
        text("""SELECT id, document_type, version, title, content
                FROM professional_onboarding_documents
                WHERE status='ACTIVE' AND deleted_at IS NULL
                  AND (document_type='PLATFORM_TERMS' OR (document_type='UNIT_POLICY' AND tenant_id=:tenant_id))
                ORDER BY document_type ASC"""),
        {"tenant_id": link["tenant_id"]},
    )
    rows = [dict(row) for row in documents.mappings().all()]
    types = {row["document_type"] for row in rows}
    if types != {"PLATFORM_TERMS", "UNIT_POLICY"}:
        raise HTTPException(status_code=409, detail="ONBOARDING_DOCUMENTS_NOT_CONFIGURED")
    return PublicOnboarding(tenant_name=link["tenant_name"], documents=rows)


@router.post("/public/{token}", response_model=ProfessionalOnboardingRequest, status_code=status.HTTP_201_CREATED)
async def submit_onboarding(token: str, payload: ProfessionalOnboardingSubmit, session: SessionDependency) -> ProfessionalOnboardingRequest:
    link_result = await session.execute(
        text("""SELECT l.id, l.tenant_id, t.name AS tenant_name
                FROM professional_onboarding_links l JOIN tenants t ON t.id=l.tenant_id
                WHERE l.token_hash=:token_hash AND l.status='ACTIVE' AND l.deleted_at IS NULL
                  AND (l.expires_at IS NULL OR l.expires_at > now()) AND t.status='ACTIVE' LIMIT 1"""),
        {"token_hash": _hash_token(token)},
    )
    link = link_result.mappings().one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Onboarding link not found.")
    documents = await session.execute(
        text("""SELECT id, document_type, version FROM professional_onboarding_documents
                WHERE status='ACTIVE' AND deleted_at IS NULL
                  AND (document_type='PLATFORM_TERMS' OR (document_type='UNIT_POLICY' AND tenant_id=:tenant_id))"""),
        {"tenant_id": link["tenant_id"]},
    )
    required = {row["id"]: dict(row) for row in documents.mappings().all()}
    accepted = set(payload.accepted_document_ids)
    if len(required) != 2 or accepted != set(required):
        raise HTTPException(status_code=422, detail="ALL_CURRENT_ONBOARDING_DOCUMENTS_MUST_BE_ACCEPTED")
    duplicate = await session.execute(
        text("""SELECT 1 FROM professional_onboarding_requests
                WHERE tenant_id=:tenant_id AND lower(email)=lower(:email)
                  AND status='PENDING_APPROVAL' AND deleted_at IS NULL LIMIT 1"""),
        {"tenant_id": link["tenant_id"], "email": str(payload.email)},
    )
    if duplicate.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="PROFESSIONAL_ONBOARDING_ALREADY_PENDING")
    created = await session.execute(
        text("""INSERT INTO professional_onboarding_requests
                (tenant_id,onboarding_link_id,name,email,phone,profession,council_type,council_number)
                VALUES (:tenant_id,:link_id,:name,:email,:phone,:profession,:council_type,:council_number)
                RETURNING id, tenant_id, name, email, phone, profession, council_type, council_number, status, created_at"""),
        {"tenant_id": link["tenant_id"], "link_id": link["id"], **payload.model_dump(exclude={"accepted_document_ids"})},
    )
    row = dict(created.mappings().one())
    for document_id, document in required.items():
        await session.execute(
            text("""INSERT INTO professional_onboarding_acceptances
                    (request_id,document_id,document_version) VALUES (:request_id,:document_id,:version)"""),
            {"request_id": row["id"], "document_id": document_id, "version": document["version"]},
        )
    await session.commit()
    return ProfessionalOnboardingRequest(tenant_name=link["tenant_name"], **row)


@router.get("/requests", response_model=list[ProfessionalOnboardingRequest])
async def list_requests(session: SessionDependency, context: TenantContextDependency) -> list[ProfessionalOnboardingRequest]:
    require_permission(context, Permission.TENANT_ADMIN)
    result = await session.execute(
        text("""SELECT r.id,r.tenant_id,t.name AS tenant_name,r.name,r.email,r.phone,r.profession,
                       r.council_type,r.council_number,r.status,r.created_at
                FROM professional_onboarding_requests r JOIN tenants t ON t.id=r.tenant_id
                WHERE r.tenant_id=:tenant_id AND r.deleted_at IS NULL ORDER BY r.created_at DESC"""),
        {"tenant_id": context.tenant_id},
    )
    return [ProfessionalOnboardingRequest.model_validate(dict(row)) for row in result.mappings().all()]


@router.post("/requests/{request_id}/approve", response_model=ProfessionalOnboardingRequest)
async def approve_request(request_id: UUID, session: SessionDependency, context: TenantContextDependency) -> ProfessionalOnboardingRequest:
    require_permission(context, Permission.TENANT_ADMIN)
    result = await session.execute(
        text("""SELECT r.*, t.name AS tenant_name FROM professional_onboarding_requests r
                JOIN tenants t ON t.id=r.tenant_id
                WHERE r.id=:request_id AND r.tenant_id=:tenant_id AND r.status='PENDING_APPROVAL'
                  AND r.deleted_at IS NULL FOR UPDATE OF r"""),
        {"request_id": request_id, "tenant_id": context.tenant_id},
    )
    request = result.mappings().one_or_none()
    if request is None:
        raise HTTPException(status_code=404, detail="Pending onboarding request not found.")
    professional = await session.execute(
        text("""INSERT INTO professionals
                (tenant_id,name,email,phone,profession,council_type,council_number,status)
                VALUES (:tenant_id,:name,:email,:phone,:profession,:council_type,:council_number,'ACTIVE')
                RETURNING id"""),
        {key: request[key] for key in ("tenant_id","name","email","phone","profession","council_type","council_number")},
    )
    professional_id = professional.scalar_one()
    invitation = await session.execute(
        text("""INSERT INTO professional_access_invitations
                (tenant_id,professional_id,email,invited_by_external_user_id)
                VALUES (:tenant_id,:professional_id,:email,:actor) RETURNING id"""),
        {"tenant_id": context.tenant_id, "professional_id": professional_id, "email": request["email"], "actor": context.external_user_id},
    )
    invitation_id = invitation.scalar_one()
    try:
        send_professional_access_invitation(
            to_email=request["email"], professional_name=request["name"], tenant_name=request["tenant_name"]
        )
    except RuntimeError as exc:
        await session.rollback()
        raise HTTPException(status_code=503, detail="PROFESSIONAL_INVITATION_EMAIL_FAILED") from exc
    await session.execute(
        text("""UPDATE professional_onboarding_requests
                SET status='APPROVED', reviewed_by_external_user_id=:actor, reviewed_at=now(),
                    professional_id=:professional_id, updated_at=now() WHERE id=:request_id"""),
        {"actor": context.external_user_id, "professional_id": professional_id, "request_id": request_id},
    )
    await create_audit_log(
        session, tenant_id=context.tenant_id, actor_external_user_id=context.external_user_id,
        action="PROFESSIONAL_ONBOARDING_APPROVED", entity_type="professional_onboarding_request",
        entity_id=request_id, metadata={"professional_id": str(professional_id), "invitation_id": str(invitation_id)},
    )
    await session.commit()
    response = dict(request)
    response["status"] = "APPROVED"
    return ProfessionalOnboardingRequest.model_validate(response)
