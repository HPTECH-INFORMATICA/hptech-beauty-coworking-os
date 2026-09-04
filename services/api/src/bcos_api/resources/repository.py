"""Tenant-scoped persistence for BCOS resources."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.resources.domain import Resource, ResourceStatus


def _resource_from_row(row: dict[str, object]) -> Resource:
    """Map one database row to the Resource domain model."""

    return Resource(
        id=row["id"],  # type: ignore[arg-type]
        tenant_id=row["tenant_id"],  # type: ignore[arg-type]
        unit_id=row["unit_id"],  # type: ignore[arg-type]
        category_id=row["category_id"],  # type: ignore[arg-type]
        name=row["name"],  # type: ignore[arg-type]
        operational_status=ResourceStatus(
            row["operational_status"]  # type: ignore[arg-type]
        ),
        buffer_before_minutes=row["buffer_before_minutes"],  # type: ignore[arg-type]
        buffer_after_minutes=row["buffer_after_minutes"],  # type: ignore[arg-type]
        active=row["active"],  # type: ignore[arg-type]
    )


async def list_resources(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unit_id: UUID | None = None,
    category_id: UUID | None = None,
) -> list[Resource]:
    """List non-deleted resources within one tenant."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                unit_id,
                category_id,
                name,
                operational_status,
                buffer_before_minutes,
                buffer_after_minutes,
                active
            FROM resources
            WHERE tenant_id = :tenant_id
              AND deleted_at IS NULL
              AND (:unit_id IS NULL OR unit_id = :unit_id)
              AND (:category_id IS NULL OR category_id = :category_id)
            ORDER BY name, id
            """
        ),
        {
            "tenant_id": tenant_id,
            "unit_id": unit_id,
            "category_id": category_id,
        },
    )

    return [
        _resource_from_row(dict(row))
        for row in result.mappings().all()
    ]


async def get_resource(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    resource_id: UUID,
) -> Resource | None:
    """Load one non-deleted resource within one tenant."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                unit_id,
                category_id,
                name,
                operational_status,
                buffer_before_minutes,
                buffer_after_minutes,
                active
            FROM resources
            WHERE id = :resource_id
              AND tenant_id = :tenant_id
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {
            "resource_id": resource_id,
            "tenant_id": tenant_id,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _resource_from_row(dict(row))


async def create_resource(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unit_id: UUID,
    category_id: UUID,
    name: str,
    buffer_before_minutes: int,
    buffer_after_minutes: int,
    active: bool,
) -> Resource:
    """Create one resource inside the authorized tenant."""

    result = await session.execute(
        text(
            """
            INSERT INTO resources (
                tenant_id,
                unit_id,
                category_id,
                name,
                buffer_before_minutes,
                buffer_after_minutes,
                active
            )
            VALUES (
                :tenant_id,
                :unit_id,
                :category_id,
                :name,
                :buffer_before_minutes,
                :buffer_after_minutes,
                :active
            )
            RETURNING
                id,
                tenant_id,
                unit_id,
                category_id,
                name,
                operational_status,
                buffer_before_minutes,
                buffer_after_minutes,
                active
            """
        ),
        {
            "tenant_id": tenant_id,
            "unit_id": unit_id,
            "category_id": category_id,
            "name": name,
            "buffer_before_minutes": buffer_before_minutes,
            "buffer_after_minutes": buffer_after_minutes,
            "active": active,
        },
    )

    row = result.mappings().one()

    return _resource_from_row(dict(row))


async def update_resource(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    resource_id: UUID,
    unit_id: UUID,
    category_id: UUID,
    name: str,
    operational_status: ResourceStatus,
    buffer_before_minutes: int,
    buffer_after_minutes: int,
    active: bool,
) -> Resource | None:
    """Update one resource without crossing tenant boundaries."""

    result = await session.execute(
        text(
            """
            UPDATE resources
            SET
                unit_id = :unit_id,
                category_id = :category_id,
                name = :name,
                operational_status = :operational_status,
                buffer_before_minutes = :buffer_before_minutes,
                buffer_after_minutes = :buffer_after_minutes,
                active = :active,
                updated_at = now()
            WHERE id = :resource_id
              AND tenant_id = :tenant_id
              AND deleted_at IS NULL
            RETURNING
                id,
                tenant_id,
                unit_id,
                category_id,
                name,
                operational_status,
                buffer_before_minutes,
                buffer_after_minutes,
                active
            """
        ),
        {
            "tenant_id": tenant_id,
            "resource_id": resource_id,
            "unit_id": unit_id,
            "category_id": category_id,
            "name": name,
            "operational_status": operational_status.value,
            "buffer_before_minutes": buffer_before_minutes,
            "buffer_after_minutes": buffer_after_minutes,
            "active": active,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _resource_from_row(dict(row))
