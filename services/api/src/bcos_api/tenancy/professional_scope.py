"""Professional own-scope resolution."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.rbac import (
    Permission,
    PermissionDenied,
    require_permission,
)


class ProfessionalScopeDenied(Exception):
    """Raised when professional own-scope cannot be resolved."""


@dataclass(frozen=True)
class ProfessionalScope:
    """Professional identity authorized within its own tenant scope."""

    professional_id: UUID
    tenant_id: UUID
    external_user_id: str


async def resolve_professional_scope(
    session: AsyncSession,
    *,
    context: TenantContext,
) -> ProfessionalScope:
    """Resolve the authenticated professional without trusting client IDs."""

    if context.role is not MembershipRole.PROFESSIONAL:
        raise PermissionDenied(
            "Authenticated identity is not operating as a professional."
        )

    require_permission(
        context,
        Permission.PROFESSIONAL_OWN,
    )

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                external_user_id
            FROM professionals
            WHERE tenant_id = :tenant_id
              AND external_user_id = :external_user_id
              AND status = 'ACTIVE'
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {
            "tenant_id": context.tenant_id,
            "external_user_id": context.external_user_id,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        raise ProfessionalScopeDenied(
            "Authenticated professional does not have an active "
            "professional profile in the requested tenant."
        )

    return ProfessionalScope(
        professional_id=row["id"],
        tenant_id=row["tenant_id"],
        external_user_id=row["external_user_id"],
    )
