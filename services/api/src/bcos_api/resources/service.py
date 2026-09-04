"""Application service for BCOS resources."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.resource_categories.repository import get_resource_category
from bcos_api.resources.domain import (
    Resource,
    ResourceStatus,
    validate_resource_buffer,
    validate_resource_name,
)
from bcos_api.resources.repository import (
    create_resource,
    get_resource,
    list_resources,
    update_resource,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.rbac import Permission, require_permission
from bcos_api.units.repository import get_unit


class ResourceNotFound(Exception):
    """Raised when a resource is not visible inside the authorized tenant."""


class ResourceUnitNotFound(Exception):
    """Raised when the requested unit is not visible inside the tenant."""


class ResourceCategoryNotFound(Exception):
    """Raised when the requested category is not visible inside the tenant."""


async def _validate_resource_relations(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unit_id: UUID,
    category_id: UUID,
) -> None:
    """Validate that unit and category belong to the same tenant."""

    unit = await get_unit(
        session,
        tenant_id=tenant_id,
        unit_id=unit_id,
    )

    if unit is None:
        raise ResourceUnitNotFound("Unit was not found.")

    category = await get_resource_category(
        session,
        tenant_id=tenant_id,
        category_id=category_id,
    )

    if category is None:
        raise ResourceCategoryNotFound(
            "Resource category was not found."
        )


async def list_tenant_resources(
    session: AsyncSession,
    *,
    context: TenantContext,
    unit_id: UUID | None = None,
    category_id: UUID | None = None,
) -> list[Resource]:
    """List resources visible to an operational tenant member."""

    require_permission(context, Permission.OPERATIONS)

    return await list_resources(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
        category_id=category_id,
    )


async def get_tenant_resource(
    session: AsyncSession,
    *,
    context: TenantContext,
    resource_id: UUID,
) -> Resource:
    """Get one resource without allowing cross-tenant lookup."""

    require_permission(context, Permission.OPERATIONS)

    resource = await get_resource(
        session,
        tenant_id=context.tenant_id,
        resource_id=resource_id,
    )

    if resource is None:
        raise ResourceNotFound("Resource was not found.")

    return resource


async def create_tenant_resource(
    session: AsyncSession,
    *,
    context: TenantContext,
    unit_id: UUID,
    category_id: UUID,
    name: str,
    buffer_before_minutes: int,
    buffer_after_minutes: int,
    active: bool,
) -> Resource:
    """Create a validated resource inside the authorized tenant."""

    require_permission(context, Permission.OPERATIONS)

    normalized_name = validate_resource_name(name)
    validated_before = validate_resource_buffer(
        buffer_before_minutes,
        field_name="buffer_before_minutes",
    )
    validated_after = validate_resource_buffer(
        buffer_after_minutes,
        field_name="buffer_after_minutes",
    )

    await _validate_resource_relations(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
        category_id=category_id,
    )

    return await create_resource(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
        category_id=category_id,
        name=normalized_name,
        buffer_before_minutes=validated_before,
        buffer_after_minutes=validated_after,
        active=active,
    )


async def update_tenant_resource(
    session: AsyncSession,
    *,
    context: TenantContext,
    resource_id: UUID,
    unit_id: UUID,
    category_id: UUID,
    name: str,
    operational_status: ResourceStatus,
    buffer_before_minutes: int,
    buffer_after_minutes: int,
    active: bool,
) -> Resource:
    """Update a validated resource inside the authorized tenant."""

    require_permission(context, Permission.OPERATIONS)

    normalized_name = validate_resource_name(name)
    validated_before = validate_resource_buffer(
        buffer_before_minutes,
        field_name="buffer_before_minutes",
    )
    validated_after = validate_resource_buffer(
        buffer_after_minutes,
        field_name="buffer_after_minutes",
    )

    await _validate_resource_relations(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
        category_id=category_id,
    )

    resource = await update_resource(
        session,
        tenant_id=context.tenant_id,
        resource_id=resource_id,
        unit_id=unit_id,
        category_id=category_id,
        name=normalized_name,
        operational_status=operational_status,
        buffer_before_minutes=validated_before,
        buffer_after_minutes=validated_after,
        active=active,
    )

    if resource is None:
        raise ResourceNotFound("Resource was not found.")

    return resource
