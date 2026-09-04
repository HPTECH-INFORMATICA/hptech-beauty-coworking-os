"""Application service for BCOS units."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.rbac import Permission, require_permission
from bcos_api.units.domain import (
    Unit,
    validate_unit_name,
    validate_unit_timezone,
)
from bcos_api.units.repository import (
    create_unit,
    get_unit,
    list_units,
    update_unit,
)


class UnitNotFound(Exception):
    """Raised when a unit is not visible inside the authorized tenant."""


async def list_tenant_units(
    session: AsyncSession,
    *,
    context: TenantContext,
) -> list[Unit]:
    """List units visible to an operational tenant member."""

    require_permission(context, Permission.OPERATIONS)

    return await list_units(
        session,
        tenant_id=context.tenant_id,
    )


async def get_tenant_unit(
    session: AsyncSession,
    *,
    context: TenantContext,
    unit_id: UUID,
) -> Unit:
    """Get one unit without allowing cross-tenant lookup."""

    require_permission(context, Permission.OPERATIONS)

    unit = await get_unit(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
    )

    if unit is None:
        raise UnitNotFound("Unit was not found.")

    return unit


async def create_tenant_unit(
    session: AsyncSession,
    *,
    context: TenantContext,
    name: str,
    timezone: str,
    active: bool,
) -> Unit:
    """Create a validated unit inside the authorized tenant."""

    require_permission(context, Permission.OPERATIONS)

    normalized_name = validate_unit_name(name)
    normalized_timezone = validate_unit_timezone(timezone)

    return await create_unit(
        session,
        tenant_id=context.tenant_id,
        name=normalized_name,
        timezone=normalized_timezone,
        active=active,
    )


async def update_tenant_unit(
    session: AsyncSession,
    *,
    context: TenantContext,
    unit_id: UUID,
    name: str,
    timezone: str,
    active: bool,
) -> Unit:
    """Update a validated unit inside the authorized tenant."""

    require_permission(context, Permission.OPERATIONS)

    normalized_name = validate_unit_name(name)
    normalized_timezone = validate_unit_timezone(timezone)

    unit = await update_unit(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
        name=normalized_name,
        timezone=normalized_timezone,
        active=active,
    )

    if unit is None:
        raise UnitNotFound("Unit was not found.")

    return unit
