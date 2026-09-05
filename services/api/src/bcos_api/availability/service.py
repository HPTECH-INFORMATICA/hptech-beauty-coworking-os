"""Application service for BCOS availability."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.availability.domain import (
    Availability,
    validate_availability_interval,
)
from bcos_api.availability.repository import list_resource_availability
from bcos_api.resource_categories.repository import get_resource_category
from bcos_api.resources.repository import get_resource
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.rbac import Permission, require_permission
from bcos_api.units.repository import get_unit


class AvailabilityUnitNotFound(Exception):
    """Raised when the requested unit is not visible inside the tenant."""


class AvailabilityResourceNotFound(Exception):
    """Raised when the requested resource is not valid for the unit."""


class AvailabilityCategoryNotFound(Exception):
    """Raised when the requested category is not visible inside the tenant."""


async def get_tenant_availability(
    session: AsyncSession,
    *,
    context: TenantContext,
    unit_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    resource_id: UUID | None = None,
    category_id: UUID | None = None,
) -> list[Availability]:
    """Calculate preventive availability inside the authorized tenant."""

    require_permission(context, Permission.OPERATIONS)

    validated_starts_at, validated_ends_at = validate_availability_interval(
        starts_at,
        ends_at,
    )

    unit = await get_unit(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
    )

    if unit is None:
        raise AvailabilityUnitNotFound("Unit was not found.")

    if resource_id is not None:
        resource = await get_resource(
            session,
            tenant_id=context.tenant_id,
            resource_id=resource_id,
        )

        if resource is None or resource.unit_id != unit_id:
            raise AvailabilityResourceNotFound(
                "Resource was not found for the requested unit."
            )

        if category_id is not None and resource.category_id != category_id:
            raise AvailabilityResourceNotFound(
                "Resource was not found for the requested category."
            )

    if category_id is not None:
        category = await get_resource_category(
            session,
            tenant_id=context.tenant_id,
            category_id=category_id,
        )

        if category is None:
            raise AvailabilityCategoryNotFound(
                "Resource category was not found."
            )

    return await list_resource_availability(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
        starts_at=validated_starts_at,
        ends_at=validated_ends_at,
        resource_id=resource_id,
        category_id=category_id,
    )
