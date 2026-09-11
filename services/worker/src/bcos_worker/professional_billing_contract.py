"""Historical professional Billing contract resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
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
    lifecycle_mode: str | None
    lifecycle_weekday: int | None
    lifecycle_biweekly_anchor: date | None
    lifecycle_month_day: int | None
    lifecycle_closing_time: time | None
    cycle_allocation_policy: str | None


def _validate_contract_configuration(
    *,
    invoice_mode: str,
    lifecycle_mode: str | None,
    lifecycle_weekday: int | None,
    lifecycle_biweekly_anchor: date | None,
    lifecycle_month_day: int | None,
    lifecycle_closing_time: time | None,
    cycle_allocation_policy: str | None,
) -> None:
    if invoice_mode == "PER_USAGE":
        if any(
            value is not None
            for value in (
                lifecycle_mode,
                lifecycle_weekday,
                lifecycle_biweekly_anchor,
                lifecycle_month_day,
                lifecycle_closing_time,
                cycle_allocation_policy,
            )
        ):
            raise ProfessionalBillingContractError(
                "PER_USAGE contract cannot define accumulated Billing lifecycle"
            )
        return

    if invoice_mode != "ACCUMULATED_OPEN_INVOICE":
        raise ProfessionalBillingContractError(
            "unsupported professional Billing invoice mode"
        )

    if cycle_allocation_policy not in {
        "USAGE_COMPLETION",
        "FIXED_CUTOFF_SPLIT",
    }:
        raise ProfessionalBillingContractError(
            "accumulated Billing contract has invalid cycle allocation policy"
        )

    if lifecycle_mode == "WEEKLY":
        if (
            lifecycle_weekday is None
            or not 0 <= lifecycle_weekday <= 6
            or lifecycle_closing_time is None
            or lifecycle_biweekly_anchor is not None
            or lifecycle_month_day is not None
        ):
            raise ProfessionalBillingContractError(
                "invalid WEEKLY Billing lifecycle configuration"
            )
        return

    if lifecycle_mode == "BIWEEKLY":
        if (
            lifecycle_biweekly_anchor is None
            or lifecycle_closing_time is None
            or lifecycle_weekday is not None
            or lifecycle_month_day is not None
        ):
            raise ProfessionalBillingContractError(
                "invalid BIWEEKLY Billing lifecycle configuration"
            )
        return

    if lifecycle_mode == "MONTHLY":
        if (
            lifecycle_month_day is None
            or not 1 <= lifecycle_month_day <= 31
            or lifecycle_closing_time is None
            or lifecycle_weekday is not None
            or lifecycle_biweekly_anchor is not None
        ):
            raise ProfessionalBillingContractError(
                "invalid MONTHLY Billing lifecycle configuration"
            )
        return

    if lifecycle_mode == "MANUAL":
        if any(
            value is not None
            for value in (
                lifecycle_weekday,
                lifecycle_biweekly_anchor,
                lifecycle_month_day,
                lifecycle_closing_time,
            )
        ):
            raise ProfessionalBillingContractError(
                "MANUAL Billing lifecycle cannot define automatic cutoff fields"
            )
        return

    raise ProfessionalBillingContractError(
        "unsupported accumulated Billing lifecycle mode"
    )


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
                valid_until,
                lifecycle_mode::text AS lifecycle_mode,
                lifecycle_weekday,
                lifecycle_biweekly_anchor,
                lifecycle_month_day,
                lifecycle_closing_time,
                cycle_allocation_policy::text AS cycle_allocation_policy
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

    _validate_contract_configuration(
        invoice_mode=row["invoice_mode"],
        lifecycle_mode=row["lifecycle_mode"],
        lifecycle_weekday=row["lifecycle_weekday"],
        lifecycle_biweekly_anchor=row["lifecycle_biweekly_anchor"],
        lifecycle_month_day=row["lifecycle_month_day"],
        lifecycle_closing_time=row["lifecycle_closing_time"],
        cycle_allocation_policy=row["cycle_allocation_policy"],
    )

    return ProfessionalBillingContract(
        id=row["id"],
        tenant_id=row["tenant_id"],
        professional_id=row["professional_id"],
        invoice_mode=row["invoice_mode"],
        valid_from=row["valid_from"],
        valid_until=row["valid_until"],
        lifecycle_mode=row["lifecycle_mode"],
        lifecycle_weekday=row["lifecycle_weekday"],
        lifecycle_biweekly_anchor=row["lifecycle_biweekly_anchor"],
        lifecycle_month_day=row["lifecycle_month_day"],
        lifecycle_closing_time=row["lifecycle_closing_time"],
        cycle_allocation_policy=row["cycle_allocation_policy"],
    )
