"""Tenant-scoped persistence for BCOS resource categories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.resource_categories.domain import ResourceCategory


def _resource_category_from_row(
    row: dict[str, object],
) -> ResourceCategory:
    """Map one database row to the ResourceCategory domain model."""

    return ResourceCategory(
        id=row["id"],  # type: ignore[arg-type]
        tenant_id=row["tenant_id"],  # type: ignore[arg-type]
        name=row["name"],  # type: ignore[arg-type]
        active=row["active"],  # type: ignore[arg-type]
    )


async def list_resource_categories(
    session: AsyncSession,
    *,
    tenant_id: UUID,
) -> list[ResourceCategory]:
    """List non-deleted resource categories within one tenant."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                name,
                active
            FROM resource_categories
            WHERE tenant_id = :tenant_id
              AND deleted_at IS NULL
            ORDER BY name, id
            """
        ),
        {"tenant_id": tenant_id},
    )

    return [
        _resource_category_from_row(dict(row))
        for row in result.mappings().all()
    ]


async def get_resource_category(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    category_id: UUID,
) -> ResourceCategory | None:
    """Load one non-deleted resource category within one tenant."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                name,
                active
            FROM resource_categories
            WHERE id = :category_id
              AND tenant_id = :tenant_id
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {
            "category_id": category_id,
            "tenant_id": tenant_id,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _resource_category_from_row(dict(row))


async def create_resource_category(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    name: str,
    active: bool,
) -> ResourceCategory:
    """Create one resource category inside the authorized tenant."""

    result = await session.execute(
        text(
            """
            INSERT INTO resource_categories (
                tenant_id,
                name,
                active
            )
            VALUES (
                :tenant_id,
                :name,
                :active
            )
            RETURNING
                id,
                tenant_id,
                name,
                active
            """
        ),
        {
            "tenant_id": tenant_id,
            "name": name,
            "active": active,
        },
    )

    row = result.mappings().one()

    return _resource_category_from_row(dict(row))
