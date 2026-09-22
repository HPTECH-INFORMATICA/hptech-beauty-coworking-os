"""Tenant membership persistence queries."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.tenancy.membership import (
    MembershipRole,
    MembershipStatus,
    TenantMembership,
)


async def tenant_is_active(
    session: AsyncSession,
    *,
    tenant_id: UUID,
) -> bool:
    """Return whether the commercial tenant is ACTIVE."""

    result = await session.execute(
        text(
            """
            SELECT status::text
            FROM tenants
            WHERE id = :tenant_id
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id},
    )
    return result.scalar_one_or_none() == "ACTIVE"


async def get_membership(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    external_user_id: str,
) -> TenantMembership | None:
    """Load one tenant membership for an authenticated external identity."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                external_user_id,
                role::text AS role,
                status::text AS status
            FROM tenant_memberships
            WHERE tenant_id = :tenant_id
              AND external_user_id = :external_user_id
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {
            "tenant_id": tenant_id,
            "external_user_id": external_user_id,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return TenantMembership(
        id=row["id"],
        tenant_id=row["tenant_id"],
        external_user_id=row["external_user_id"],
        role=MembershipRole(row["role"]),
        status=MembershipStatus(row["status"]),
    )
