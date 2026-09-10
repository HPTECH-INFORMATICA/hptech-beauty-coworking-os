"""Pure monetary calculation for approved BCOS M7 overtime rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANTUM = Decimal("0.01")
MINUTES_PER_HOUR = 60


class OvertimeMoneyError(ValueError):
    """Raised when overtime cannot be calculated under the frozen contract."""


@dataclass(frozen=True, slots=True)
class OvertimeMoneyResult:
    completed_minutes: int
    full_hours: int
    remainder_minutes: int
    unquantized_amount: Decimal
    amount: Decimal


def quantize_money(value: Decimal) -> Decimal:
    """Materialize a BRL monetary value using the approved T12 contract."""
    if not value.is_finite():
        raise OvertimeMoneyError("monetary value must be finite")

    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_overtime_amount(
    *,
    hourly_price_amount: Decimal,
    completed_minutes: int,
    proportional_until_minutes: int,
    full_hour_from_minutes: int,
) -> OvertimeMoneyResult:
    """Calculate overtime using the Coworking rule frozen in pricing_snapshot."""

    if not hourly_price_amount.is_finite():
        raise OvertimeMoneyError("hourly_price_amount must be finite")

    for name, value in (
        ("completed_minutes", completed_minutes),
        ("proportional_until_minutes", proportional_until_minutes),
        ("full_hour_from_minutes", full_hour_from_minutes),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise OvertimeMoneyError(f"{name} must be an integer")

    if completed_minutes < 0:
        raise OvertimeMoneyError("completed_minutes must not be negative")

    full_hours, remainder_minutes = divmod(
        completed_minutes,
        MINUTES_PER_HOUR,
    )

    unquantized = hourly_price_amount * Decimal(full_hours)

    if remainder_minutes:
        if remainder_minutes <= proportional_until_minutes:
            unquantized += (
                hourly_price_amount
                / Decimal(MINUTES_PER_HOUR)
                * Decimal(remainder_minutes)
            )
        elif remainder_minutes >= full_hour_from_minutes:
            unquantized += hourly_price_amount
        else:
            raise OvertimeMoneyError(
                "remaining overtime minutes are not covered by the configured "
                "proportional/full-hour rule"
            )

    return OvertimeMoneyResult(
        completed_minutes=completed_minutes,
        full_hours=full_hours,
        remainder_minutes=remainder_minutes,
        unquantized_amount=unquantized,
        amount=quantize_money(unquantized),
    )
