"""Authenticated product access resolution.

Resolves the BCOS destinations available to one already-authenticated identity
without trusting browser-supplied tenant or role claims.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.auth.dependencies import get_authenticated_identity
from bcos_api.auth.identity import AuthenticatedIdentity
from bcos_api.db.session import get_async_session
from bcos_api.platform.domain import PlatformOperatorStatus
from bcos_api.platform.repository import get_platform_operator
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.rbac import ROLE_PERMISSIONS, Permission

router = APIRouter(prefix="/api/v1/access", tags=["Access"])
SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
IdentityDependency = Annotated[AuthenticatedIdentity, Depends(get_authenticated_identity)]


class TenantAccessOption(BaseModel):
    tenant_id: UUID
    tenant_name: str
    role: MembershipRole
    destination: Literal["/administracao", "/", "/profissional"]
    permissions: list[Permission]


class AccessResolution(BaseModel):
    platform_destination: Literal["/platform"] | None
    tenants: list[TenantAccessOption]


def _tenant_destination(role: MembershipRole) -> Literal["/administracao", "/", "/profissional"]:
    if role in {MembershipRole.OWNER, MembershipRole.ADMIN}:
        return "/administracao"
    if role is MembershipRole.RECEPTION:
        return "/"
    return "/profissional"


@router.get("", response_model=AccessResolution)
async def resolve_access(
    session: SessionDependency,
    identity: IdentityDependency,
) -> AccessResolution:
    operator = await get_platform_operator(
        session,
        external_user_id=identity.external_user_id,
    )
    result = await session.execute(
        text(
            """SELECT m.id AS membership_id, m.tenant_id, t.name AS tenant_name, m.role::text AS role
            FROM tenant_memberships AS m
            JOIN tenants AS t ON t.id = m.tenant_id
            WHERE m.external_user_id = :external_user_id
              AND m.status = 'ACTIVE'
              AND m.deleted_at IS NULL
              AND t.status = 'ACTIVE'
            ORDER BY t.name ASC, m.tenant_id ASC"""
        ),
        {"external_user_id": identity.external_user_id},
    )
    tenants: list[TenantAccessOption] = []
    for row in result.mappings().all():
        role = MembershipRole(row["role"])
        effective = set(ROLE_PERMISSIONS[role])
        override_result = await session.execute(
            text("""SELECT permission, granted FROM tenant_membership_permission_overrides
                    WHERE tenant_id=:tenant_id AND membership_id=:membership_id"""),
            {"tenant_id": row["tenant_id"], "membership_id": row["membership_id"]},
        )
        for override in override_result.mappings().all():
            permission = Permission(override["permission"])
            effective.add(permission) if override["granted"] else effective.discard(permission)
        if role is MembershipRole.OWNER:
            effective = set(ROLE_PERMISSIONS[MembershipRole.OWNER])
        tenants.append(TenantAccessOption(
            tenant_id=row["tenant_id"], tenant_name=row["tenant_name"], role=role,
            destination=_tenant_destination(role),
            permissions=sorted(effective, key=lambda item: item.value),
        ))
    platform_destination: Literal["/platform"] | None = (
        "/platform"
        if operator is not None and operator.status is PlatformOperatorStatus.ACTIVE
        else None
    )
    return AccessResolution(
        platform_destination=platform_destination,
        tenants=tenants,
    )
