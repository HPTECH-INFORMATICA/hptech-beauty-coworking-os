"""Application service for BCOS unit reception hours."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.reception_hours.domain import (
    ReceptionHours,
    validate_reception_hours,
)
from bcos_api.reception_hours.repository import (
    list_reception_hours,
    replace_reception_hours,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.rbac import Permission, require_permission
from bcos_api.units.repository import get_unit


class ReceptionHoursUnitNotFound(Exception):
    """Raised when the requested unit is not visible in the tenant."""


class InvalidReceptionHoursSet(Exception):
    """Raised when a reception-hours collection is invalid."""


@dataclass(frozen=True)
class ReceptionHoursInput:
    """Input for one weekday reception-hours definition."""

    day_of_week: int
    opens_at: time | None
    closes_at: time | None
    is_closed: bool


async def get_unit_reception_hours(
    session: AsyncSession,
    *,
    context: TenantContext,
    unit_id: UUID,
) -> list[ReceptionHours]:
    """Get reception hours for a unit inside the authorized tenant."""

    require_permission(context, Permission.OPERATIONS)

    unit = await get_unit(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
    )

    if unit is None:
        raise ReceptionHoursUnitNotFound("Unit was not found.")

    return await list_reception_hours(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
    )


async def replace_unit_reception_hours(
    session: AsyncSession,
    *,
    context: TenantContext,
    unit_id: UUID,
    entries: list[ReceptionHoursInput],
) -> list[ReceptionHours]:
    """Validate and replace the complete reception-hours set."""

    require_permission(context, Permission.OPERATIONS)

    if not entries:
        raise InvalidReceptionHoursSet(
            "At least one reception-hours entry is required."
        )

    if len(entries) > 7:
        raise InvalidReceptionHoursSet(
            "Reception hours must not contain more than seven entries."
        )

    days = [entry.day_of_week for entry in entries]

    if len(days) != len(set(days)):
        raise InvalidReceptionHoursSet(
            "Reception hours must not contain duplicate weekdays."
        )

    validated_entries = [
        validate_reception_hours(
            day_of_week=entry.day_of_week,
            opens_at=entry.opens_at,
            closes_at=entry.closes_at,
            is_closed=entry.is_closed,
        )
        for entry in entries
    ]

    unit = await get_unit(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
    )

    if unit is None:
        raise ReceptionHoursUnitNotFound("Unit was not found.")

    return await replace_reception_hours(
        session,
        tenant_id=context.tenant_id,
        unit_id=unit_id,
        entries=validated_entries,
    )
