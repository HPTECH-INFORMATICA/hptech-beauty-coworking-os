"""Application service for BCOS resource categories."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.resource_categories.domain import (
    ResourceCategory,
    validate_resource_category_name,
)
from bcos_api.resource_categories.repository import (
    create_resource_category,
    get_resource_category,
    list_resource_categories,
    soft_delete_resource_category,
    update_resource_category,
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


class ResourceCategoryNotFound(Exception):
    """Raised when a category is not visible inside the authorized tenant."""


class ResourceCategoryDeleteConflict(Exception):
    """Raised when a category still classifies an active resource."""


async def update_tenant_resource_category(
    session: AsyncSession, *, context: TenantContext, category_id, name: str, active: bool
) -> ResourceCategory:
    """Update a validated category inside the authorized tenant."""
    require_permission(context, Permission.OPERATIONS)
    normalized_name = validate_resource_category_name(name)
    category = await update_resource_category(
        session, tenant_id=context.tenant_id, category_id=category_id,
        name=normalized_name, active=active,
    )
    if category is None:
        raise ResourceCategoryNotFound("Resource category was not found.")
    return category


async def delete_tenant_resource_category(
    session: AsyncSession, *, context: TenantContext, category_id
) -> None:
    """Remove an unused category while preserving referenced catalog history."""
    require_permission(context, Permission.OPERATIONS)
    if await get_resource_category(
        session, tenant_id=context.tenant_id, category_id=category_id
    ) is None:
        raise ResourceCategoryNotFound("Resource category was not found.")
    if not await soft_delete_resource_category(
        session, tenant_id=context.tenant_id, category_id=category_id
    ):
        raise ResourceCategoryDeleteConflict(
            "O tipo de espaço está sendo usado por um espaço. Altere ou remova o espaço antes de excluir o tipo."
        )
