"""Persistence operations for BCOS Invoice materialization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_worker.billing_cycle import BillingCycle


class InvoiceMaterializationError(RuntimeError):
    """Raised when Invoice materialization cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class InvoiceIdentity:
    id: UUID
    tenant_id: UUID
    professional_id: UUID
    source_usage_id: UUID


@dataclass(frozen=True, slots=True)
class AccumulatedInvoiceIdentity:
    id: UUID
    tenant_id: UUID
    professional_id: UUID
    professional_billing_contract_id: UUID
    billing_cycle_start: datetime | None
    billing_cycle_end: datetime | None
    manual_closed_at: datetime | None
    status: str


def _accumulated_identity_from_row(
    row,
    *,
    tenant_id: UUID,
    professional_id: UUID,
    professional_billing_contract_id: UUID,
    cycle: BillingCycle | None,
) -> AccumulatedInvoiceIdentity:
    if row["tenant_id"] != tenant_id:
        raise InvoiceMaterializationError(
            "resolved accumulated Invoice belongs to another tenant"
        )

    if row["professional_id"] != professional_id:
        raise InvoiceMaterializationError(
            "resolved accumulated Invoice belongs to another professional"
        )

    if row["professional_billing_contract_id"] != professional_billing_contract_id:
        raise InvoiceMaterializationError(
            "resolved accumulated Invoice belongs to another historical Billing contract"
        )

    if row["source_usage_id"] is not None:
        raise InvoiceMaterializationError(
            "resolved accumulated Invoice has PER_USAGE source identity"
        )

    if row["status"] != "OPEN":
        raise InvoiceMaterializationError(
            "resolved accumulated Invoice is not OPEN"
        )

    if cycle is None:
        if row["billing_cycle_start"] is not None or row["billing_cycle_end"] is not None:
            raise InvoiceMaterializationError(
                "resolved MANUAL accumulated Invoice has automatic cycle boundaries"
            )
        if row["manual_closed_at"] is not None:
            raise InvoiceMaterializationError(
                "resolved MANUAL accumulated Invoice is closed"
            )
    else:
        if row["billing_cycle_start"] != cycle.start:
            raise InvoiceMaterializationError(
                "resolved accumulated Invoice cycle start differs from expected value"
            )
        if row["billing_cycle_end"] != cycle.end:
            raise InvoiceMaterializationError(
                "resolved accumulated Invoice cycle end differs from expected value"
            )
        if row["manual_closed_at"] is not None:
            raise InvoiceMaterializationError(
                "automatic accumulated Invoice cannot have manual_closed_at"
            )

    return AccumulatedInvoiceIdentity(
        id=row["id"],
        tenant_id=row["tenant_id"],
        professional_id=row["professional_id"],
        professional_billing_contract_id=row["professional_billing_contract_id"],
        billing_cycle_start=row["billing_cycle_start"],
        billing_cycle_end=row["billing_cycle_end"],
        manual_closed_at=row["manual_closed_at"],
        status=row["status"],
    )


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


async def get_or_create_accumulated_invoice(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    professional_id: UUID,
    professional_billing_contract_id: UUID,
    cycle: BillingCycle | None,
) -> AccumulatedInvoiceIdentity:
    """Return the unique eligible accumulated Invoice for a lifecycle identity."""

    if cycle is None:
        existing_result = await session.execute(
            text(
                """
                SELECT
                    id,
                    tenant_id,
                    professional_id,
                    source_usage_id,
                    professional_billing_contract_id,
                    billing_cycle_start,
                    billing_cycle_end,
                    manual_closed_at,
                    status::text AS status
                FROM invoices
                WHERE tenant_id = :tenant_id
                  AND professional_billing_contract_id = :contract_id
                  AND source_usage_id IS NULL
                  AND billing_cycle_start IS NULL
                  AND billing_cycle_end IS NULL
                  AND manual_closed_at IS NULL
                FOR UPDATE
                """
            ),
            {
                "tenant_id": tenant_id,
                "contract_id": professional_billing_contract_id,
            },
        )
    else:
        existing_result = await session.execute(
            text(
                """
                SELECT
                    id,
                    tenant_id,
                    professional_id,
                    source_usage_id,
                    professional_billing_contract_id,
                    billing_cycle_start,
                    billing_cycle_end,
                    manual_closed_at,
                    status::text AS status
                FROM invoices
                WHERE tenant_id = :tenant_id
                  AND professional_billing_contract_id = :contract_id
                  AND source_usage_id IS NULL
                  AND billing_cycle_start = :cycle_start
                  AND billing_cycle_end = :cycle_end
                FOR UPDATE
                """
            ),
            {
                "tenant_id": tenant_id,
                "contract_id": professional_billing_contract_id,
                "cycle_start": cycle.start,
                "cycle_end": cycle.end,
            },
        )

    existing_rows = existing_result.mappings().all()

    if len(existing_rows) > 1:
        raise InvoiceMaterializationError(
            "multiple accumulated Invoices found for one lifecycle identity"
        )

    if existing_rows:
        return _accumulated_identity_from_row(
            existing_rows[0],
            tenant_id=tenant_id,
            professional_id=professional_id,
            professional_billing_contract_id=professional_billing_contract_id,
            cycle=cycle,
        )

    if cycle is None:
        inserted_result = await session.execute(
            text(
                """
                INSERT INTO invoices (
                    tenant_id,
                    professional_id,
                    source_usage_id,
                    professional_billing_contract_id,
                    billing_cycle_start,
                    billing_cycle_end,
                    manual_closed_at
                )
                VALUES (
                    :tenant_id,
                    :professional_id,
                    NULL,
                    :contract_id,
                    NULL,
                    NULL,
                    NULL
                )
                ON CONFLICT (tenant_id, professional_billing_contract_id)
                    WHERE source_usage_id IS NULL
                      AND professional_billing_contract_id IS NOT NULL
                      AND billing_cycle_start IS NULL
                      AND billing_cycle_end IS NULL
                      AND manual_closed_at IS NULL
                DO NOTHING
                RETURNING
                    id,
                    tenant_id,
                    professional_id,
                    source_usage_id,
                    professional_billing_contract_id,
                    billing_cycle_start,
                    billing_cycle_end,
                    manual_closed_at,
                    status::text AS status
                """
            ),
            {
                "tenant_id": tenant_id,
                "professional_id": professional_id,
                "contract_id": professional_billing_contract_id,
            },
        )
    else:
        inserted_result = await session.execute(
            text(
                """
                INSERT INTO invoices (
                    tenant_id,
                    professional_id,
                    source_usage_id,
                    professional_billing_contract_id,
                    billing_cycle_start,
                    billing_cycle_end,
                    manual_closed_at
                )
                VALUES (
                    :tenant_id,
                    :professional_id,
                    NULL,
                    :contract_id,
                    :cycle_start,
                    :cycle_end,
                    NULL
                )
                ON CONFLICT (
                    tenant_id,
                    professional_billing_contract_id,
                    billing_cycle_start,
                    billing_cycle_end
                )
                    WHERE source_usage_id IS NULL
                      AND professional_billing_contract_id IS NOT NULL
                      AND billing_cycle_start IS NOT NULL
                      AND billing_cycle_end IS NOT NULL
                DO NOTHING
                RETURNING
                    id,
                    tenant_id,
                    professional_id,
                    source_usage_id,
                    professional_billing_contract_id,
                    billing_cycle_start,
                    billing_cycle_end,
                    manual_closed_at,
                    status::text AS status
                """
            ),
            {
                "tenant_id": tenant_id,
                "professional_id": professional_id,
                "contract_id": professional_billing_contract_id,
                "cycle_start": cycle.start,
                "cycle_end": cycle.end,
            },
        )

    inserted = inserted_result.mappings().one_or_none()

    if inserted is not None:
        return _accumulated_identity_from_row(
            inserted,
            tenant_id=tenant_id,
            professional_id=professional_id,
            professional_billing_contract_id=professional_billing_contract_id,
            cycle=cycle,
        )

    if cycle is None:
        concurrent_result = await session.execute(
            text(
                """
                SELECT
                    id,
                    tenant_id,
                    professional_id,
                    source_usage_id,
                    professional_billing_contract_id,
                    billing_cycle_start,
                    billing_cycle_end,
                    manual_closed_at,
                    status::text AS status
                FROM invoices
                WHERE tenant_id = :tenant_id
                  AND professional_billing_contract_id = :contract_id
                  AND source_usage_id IS NULL
                  AND billing_cycle_start IS NULL
                  AND billing_cycle_end IS NULL
                  AND manual_closed_at IS NULL
                FOR UPDATE
                """
            ),
            {
                "tenant_id": tenant_id,
                "contract_id": professional_billing_contract_id,
            },
        )
    else:
        concurrent_result = await session.execute(
            text(
                """
                SELECT
                    id,
                    tenant_id,
                    professional_id,
                    source_usage_id,
                    professional_billing_contract_id,
                    billing_cycle_start,
                    billing_cycle_end,
                    manual_closed_at,
                    status::text AS status
                FROM invoices
                WHERE tenant_id = :tenant_id
                  AND professional_billing_contract_id = :contract_id
                  AND source_usage_id IS NULL
                  AND billing_cycle_start = :cycle_start
                  AND billing_cycle_end = :cycle_end
                FOR UPDATE
                """
            ),
            {
                "tenant_id": tenant_id,
                "contract_id": professional_billing_contract_id,
                "cycle_start": cycle.start,
                "cycle_end": cycle.end,
            },
        )

    concurrent_rows = concurrent_result.mappings().all()

    if len(concurrent_rows) != 1:
        raise InvoiceMaterializationError(
            "accumulated Invoice could not be created or resolved unambiguously"
        )

    return _accumulated_identity_from_row(
        concurrent_rows[0],
        tenant_id=tenant_id,
        professional_id=professional_id,
        professional_billing_contract_id=professional_billing_contract_id,
        cycle=cycle,
    )
