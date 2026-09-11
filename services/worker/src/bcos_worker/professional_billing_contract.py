"""Historical professional Billing contract resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class ProfessionalBillingContractError(RuntimeError):
    """Raised when the applicable Billing contract cannot be resolved safely."""


@dataclass(frozen=True, slots=True)
class ProfessionalBillingContract:
    id: UUID
    tenant_id: UUID
    professional_id: UUID
    invoice_mode: str
    valid_from: datetime
    valid_until: datetime | None


async def resolve_professional_billing_contract(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    professional_id: UUID,
    booking_starts_at: datetime,
) -> ProfessionalBillingContract:
    """Resolve exactly one historical contract at Booking start time."""

    if booking_starts_at.tzinfo is None:
        raise ProfessionalBillingContractError(
            "booking_starts_at must be timezone-aware"
        )

    result = await session.execute(
        text(
            """
            SELECT
                id,
                tenant_id,
                professional_id,
                invoice_mode::text AS invoice_mode,
                valid_from,
                valid_until
            FROM professional_billing_contracts
            WHERE tenant_id = :tenant_id
              AND professional_id = :professional_id
              AND valid_from <= :booking_starts_at
              AND (
                    valid_until IS NULL
                    OR :booking_starts_at < valid_until
              )
            ORDER BY valid_from DESC
            LIMIT 2
            """
        ),
        {
            "tenant_id": tenant_id,
            "professional_id": professional_id,
            "booking_starts_at": booking_starts_at,
        },
    )

    rows = result.mappings().all()

    if not rows:
        raise ProfessionalBillingContractError(
            "professional Billing contract not found for Booking start"
        )

    if len(rows) != 1:
        raise ProfessionalBillingContractError(
            "ambiguous professional Billing contract for Booking start"
        )

    row = rows[0]
    invoice_mode = row["invoice_mode"]

    if invoice_mode not in {
        "PER_USAGE",
        "ACCUMULATED_OPEN_INVOICE",
    }:
        raise ProfessionalBillingContractError(
            "unsupported professional Billing invoice mode"
        )

    return ProfessionalBillingContract(
        id=row["id"],
        tenant_id=row["tenant_id"],
        professional_id=row["professional_id"],
        invoice_mode=invoice_mode,
        valid_from=row["valid_from"],
        valid_until=row["valid_until"],
    )
