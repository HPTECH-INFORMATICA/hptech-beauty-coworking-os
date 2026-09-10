"""Pure monetary calculation for approved BCOS M7 overtime rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANTUM = Decimal("0.01")


class OvertimeMoneyError(ValueError):
    """Raised when overtime cannot be calculated under the frozen contract."""


@dataclass(frozen=True, slots=True)
class OvertimeMoneyResult:
    completed_minutes: int
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
) -> OvertimeMoneyResult:
    """Calculate monetary overtime without persistence or administrative decisions."""

    if not hourly_price_amount.is_finite():
        raise OvertimeMoneyError("hourly_price_amount must be finite")

    if isinstance(completed_minutes, bool) or not isinstance(completed_minutes, int):
        raise OvertimeMoneyError("completed_minutes must be an integer")

    if completed_minutes < 0:
        raise OvertimeMoneyError("completed_minutes must not be negative")

    if completed_minutes == 0:
        unquantized = Decimal("0")
    elif completed_minutes < 30:
        unquantized = hourly_price_amount / Decimal("60") * Decimal(completed_minutes)
    elif completed_minutes < 60:
        unquantized = hourly_price_amount
    else:
        raise OvertimeMoneyError(
            "overtime of 60 or more completed minutes requires a separately frozen "
            "multi-hour charging rule"
        )

    return OvertimeMoneyResult(
        completed_minutes=completed_minutes,
        unquantized_amount=unquantized,
        amount=quantize_money(unquantized),
    )
