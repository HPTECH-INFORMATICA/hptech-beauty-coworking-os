"""Authorized tenant context resolution."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.repository import get_membership, tenant_is_active


class TenantAccessDenied(Exception):
    """Raised when an identity cannot operate within the requested tenant."""


@dataclass(frozen=True)
class TenantContext:
    """Authorized tenant context for one authenticated identity."""

    tenant_id: UUID
    membership_id: UUID
    external_user_id: str
    role: MembershipRole


async def resolve_tenant_context(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    external_user_id: str,
) -> TenantContext:
    """Resolve and authorize an identity within one BCOS tenant."""

    if not await tenant_is_active(session, tenant_id=tenant_id):
        raise TenantAccessDenied("Requested tenant is not active.")

    membership = await get_membership(
        session,
        tenant_id=tenant_id,
        external_user_id=external_user_id,
    )

    if membership is None or not membership.is_active:
        raise TenantAccessDenied(
            "Authenticated identity does not have active access "
            "to the requested tenant."
        )

    return TenantContext(
        tenant_id=membership.tenant_id,
        membership_id=membership.id,
        external_user_id=membership.external_user_id,
        role=membership.role,
    )
