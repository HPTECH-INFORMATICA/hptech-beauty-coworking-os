"""Tenant-scoped persistence for BCOS professionals."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.professionals.domain import (
    Professional,
    ProfessionalStatus,
)


def _professional_from_row(
    row: dict[str, object],
) -> Professional:
    """Map one database row to the Professional domain model."""

    return Professional(
        id=row["id"],  # type: ignore[arg-type]
        tenant_id=row["tenant_id"],  # type: ignore[arg-type]
        external_user_id=row["external_user_id"],  # type: ignore[arg-type]
        name=row["name"],  # type: ignore[arg-type]
        email=row["email"],  # type: ignore[arg-type]
        phone=row["phone"],  # type: ignore[arg-type]
        status=ProfessionalStatus(
            row["status"]  # type: ignore[arg-type]
        ),
    )


async def list_professionals(
    session: AsyncSession,
    *,
    tenant_id: UUID,
) -> list[Professional]:
    """List non-deleted professionals belonging to one tenant."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                external_user_id,
                name,
                email,
                phone,
                status
            FROM professionals
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
        _professional_from_row(dict(row))
        for row in result.mappings().all()
    ]


async def get_professional(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    professional_id: UUID,
) -> Professional | None:
    """Load one non-deleted professional within one tenant."""

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                external_user_id,
                name,
                email,
                phone,
                status
            FROM professionals
            WHERE id = :professional_id
              AND tenant_id = :tenant_id
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {
            "professional_id": professional_id,
            "tenant_id": tenant_id,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _professional_from_row(dict(row))


async def create_professional(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    external_user_id: str | None,
    name: str,
    email: str | None,
    phone: str | None,
) -> Professional:
    """Create one professional inside the authorized tenant."""

    result = await session.execute(
        text(
            """
            INSERT INTO professionals (
                tenant_id,
                external_user_id,
                name,
                email,
                phone
            )
            VALUES (
                :tenant_id,
                :external_user_id,
                :name,
                :email,
                :phone
            )
            RETURNING
                id,
                tenant_id,
                external_user_id,
                name,
                email,
                phone,
                status
            """
        ),
        {
            "tenant_id": tenant_id,
            "external_user_id": external_user_id,
            "name": name,
            "email": email,
            "phone": phone,
        },
    )

    row = result.mappings().one()

    return _professional_from_row(dict(row))


async def update_professional(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    professional_id: UUID,
    external_user_id: str | None,
    name: str,
    email: str | None,
    phone: str | None,
    status: ProfessionalStatus,
) -> Professional | None:
    """Update one professional without crossing tenant boundaries."""

    result = await session.execute(
        text(
            """
            UPDATE professionals
            SET
                external_user_id = :external_user_id,
                name = :name,
                email = :email,
                phone = :phone,
                status = :status,
                updated_at = now()
            WHERE id = :professional_id
              AND tenant_id = :tenant_id
              AND deleted_at IS NULL
            RETURNING
                id,
                tenant_id,
                external_user_id,
                name,
                email,
                phone,
                status
            """
        ),
        {
            "tenant_id": tenant_id,
            "professional_id": professional_id,
            "external_user_id": external_user_id,
            "name": name,
            "email": email,
            "phone": phone,
            "status": status.value,
        },
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return _professional_from_row(dict(row))
