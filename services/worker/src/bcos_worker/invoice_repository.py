"""Persistence operations for BCOS Invoice materialization."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class InvoiceMaterializationError(RuntimeError):
    """Raised when Invoice materialization cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class InvoiceIdentity:
    id: UUID
    tenant_id: UUID
    professional_id: UUID
    source_usage_id: UUID


async def get_or_create_per_usage_invoice(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    professional_id: UUID,
    usage_id: UUID,
) -> InvoiceIdentity:
    """Return the unique PER_USAGE Invoice for a completed Usage."""

    existing_result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                professional_id,
                source_usage_id
            FROM invoices
            WHERE tenant_id = :tenant_id
              AND source_usage_id = :usage_id
            FOR UPDATE
            """
        ),
        {
            "tenant_id": tenant_id,
            "usage_id": usage_id,
        },
    )

    existing_rows = existing_result.mappings().all()

    if len(existing_rows) > 1:
        raise InvoiceMaterializationError(
            "multiple PER_USAGE invoices found for the same Usage"
        )

    if existing_rows:
        row = existing_rows[0]

        if row["professional_id"] != professional_id:
            raise InvoiceMaterializationError(
                "existing PER_USAGE invoice belongs to another professional"
            )

        return InvoiceIdentity(
            id=row["id"],
            tenant_id=row["tenant_id"],
            professional_id=row["professional_id"],
            source_usage_id=row["source_usage_id"],
        )

    inserted_result = await session.execute(
        text(
            """
            INSERT INTO invoices (
                tenant_id,
                professional_id,
                source_usage_id
            )
            VALUES (
                :tenant_id,
                :professional_id,
                :usage_id
            )
            ON CONFLICT (tenant_id, source_usage_id)
                WHERE source_usage_id IS NOT NULL
            DO NOTHING
            RETURNING
                id,
                tenant_id,
                professional_id,
                source_usage_id
            """
        ),
        {
            "tenant_id": tenant_id,
            "professional_id": professional_id,
            "usage_id": usage_id,
        },
    )

    inserted = inserted_result.mappings().one_or_none()

    if inserted is not None:
        return InvoiceIdentity(
            id=inserted["id"],
            tenant_id=inserted["tenant_id"],
            professional_id=inserted["professional_id"],
            source_usage_id=inserted["source_usage_id"],
        )

    concurrent_result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                professional_id,
                source_usage_id
            FROM invoices
            WHERE tenant_id = :tenant_id
              AND source_usage_id = :usage_id
            """
        ),
        {
            "tenant_id": tenant_id,
            "usage_id": usage_id,
        },
    )

    concurrent = concurrent_result.mappings().one_or_none()

    if concurrent is None:
        raise InvoiceMaterializationError(
            "PER_USAGE invoice could not be created or resolved"
        )

    if concurrent["professional_id"] != professional_id:
        raise InvoiceMaterializationError(
            "resolved PER_USAGE invoice belongs to another professional"
        )

    return InvoiceIdentity(
        id=concurrent["id"],
        tenant_id=concurrent["tenant_id"],
        professional_id=concurrent["professional_id"],
        source_usage_id=concurrent["source_usage_id"],
    )