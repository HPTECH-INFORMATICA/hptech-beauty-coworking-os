"""Tenant-scoped persistence for BCOS units."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.units.domain import Unit


def _unit_from_row(row: dict[str, object]) -> Unit:
    """Map one database row to the Unit domain model."""

    return Unit(
        id=row["id"],  # type: ignore[arg-type]
        tenant_id=row["tenant_id"],  # type: ignore[arg-type]
        name=row["name"],  # type: ignore[arg-type]
        timezone=row["timezone"],  # type: ignore[arg-type]
        active=row["active"],  # type: ignore[arg-type]
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
    )


async def list_units(
    session: AsyncSession,
    *,
    tenant_id: UUID,
) -> list[Unit]:
    """List non-deleted units within one tenant."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                name,
                timezone,
                active,
                created_at,
                updated_at
            FROM units
            WHERE tenant_id = :tenant_id
              AND deleted_at IS NULL
            ORDER BY name, id
            """
        ),
        {
            "tenant_id": tenant_id,
        },
    )

    return [
        _unit_from_row(dict(row))
        for row in result.mappings().all()
    ]


async def get_unit(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unit_id: UUID,
) -> Unit | None:
    """Load one non-deleted unit within one tenant."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                name,
                timezone,
                active,
                created_at,
                updated_at
            FROM units
            WHERE id = :unit_id
              AND tenant_id = :tenant_id
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {
            "unit_id": unit_id,
            "tenant_id": tenant_id,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _unit_from_row(dict(row))


async def create_unit(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    name: str,
    timezone: str,
    active: bool,
) -> Unit:
    """Create one unit inside the authorized tenant."""

    result = await session.execute(
        text(
            """
            INSERT INTO units (
                tenant_id,
                name,
                timezone,
                active
            )
            VALUES (
                :tenant_id,
                :name,
                :timezone,
                :active
            )
            RETURNING
                id,
                tenant_id,
                name,
                timezone,
                active,
                created_at,
                updated_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "name": name,
            "timezone": timezone,
            "active": active,
        },
    )

    row = result.mappings().one()

    return _unit_from_row(dict(row))


async def update_unit(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unit_id: UUID,
    name: str,
    timezone: str,
    active: bool,
) -> Unit | None:
    """Update one unit without crossing tenant boundaries."""

    result = await session.execute(
        text(
            """
            UPDATE units
            SET
                name = :name,
                timezone = :timezone,
                active = :active,
                updated_at = now()
            WHERE id = :unit_id
              AND tenant_id = :tenant_id
              AND deleted_at IS NULL
            RETURNING
                id,
                tenant_id,
                name,
                timezone,
                active,
                created_at,
                updated_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "unit_id": unit_id,
            "name": name,
            "timezone": timezone,
            "active": active,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _unit_from_row(dict(row))
