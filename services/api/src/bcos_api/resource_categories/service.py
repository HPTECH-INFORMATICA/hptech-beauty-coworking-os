"""Application service for BCOS resource categories."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.resource_categories.domain import (
    ResourceCategory,
    validate_resource_category_name,
)
from bcos_api.resource_categories.repository import (
    create_resource_category,
    list_resource_categories,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.rbac import Permission, require_permission


async def list_tenant_resource_categories(
    session: AsyncSession,
    *,
    context: TenantContext,
) -> list[ResourceCategory]:
    """List resource categories visible to an operational tenant member."""

    require_permission(context, Permission.OPERATIONS)

    return await list_resource_categories(
        session,
        tenant_id=context.tenant_id,
    )


async def create_tenant_resource_category(
    session: AsyncSession,
    *,
    context: TenantContext,
    name: str,
    active: bool,
) -> ResourceCategory:
    """Create a validated resource category inside the authorized tenant."""

    require_permission(context, Permission.OPERATIONS)

    normalized_name = validate_resource_category_name(name)

    return await create_resource_category(
        session,
        tenant_id=context.tenant_id,
        name=normalized_name,
        active=active,
    )
