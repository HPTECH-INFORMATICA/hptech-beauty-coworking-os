from decimal import Decimal

import pytest

from bcos_worker.overtime_money import (
    OvertimeMoneyError,
    calculate_overtime_amount,
    quantize_money,
)


def test_zero_minutes_has_zero_amount() -> None:
    result = calculate_overtime_amount(
        hourly_price_amount=Decimal("100.00"),
        completed_minutes=0,
    )

    assert result.amount == Decimal("0.00")


def test_one_minute_is_proportional_and_half_up_quantized() -> None:
    result = calculate_overtime_amount(
        hourly_price_amount=Decimal("100.00"),
        completed_minutes=1,
    )

    assert result.unquantized_amount == Decimal("100.00") / Decimal("60")
    assert result.amount == Decimal("1.67")


def test_twenty_nine_minutes_remain_proportional() -> None:
    result = calculate_overtime_amount(
        hourly_price_amount=Decimal("100.00"),
        completed_minutes=29,
    )

    assert result.amount == Decimal("48.33")


def test_exactly_thirty_minutes_charge_full_hour() -> None:
    result = calculate_overtime_amount(
        hourly_price_amount=Decimal("100.00"),
        completed_minutes=30,
    )

    assert result.amount == Decimal("100.00")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("1.664"), Decimal("1.66")),
        (Decimal("1.665"), Decimal("1.67")),
        (Decimal("1.666"), Decimal("1.67")),
    ],
)
def test_quantize_money_uses_round_half_up(
    value: Decimal,
    expected: Decimal,
) -> None:
    assert quantize_money(value) == expected


@pytest.mark.parametrize("minutes", [30, 31, 45, 59])
def test_thirty_through_fifty_nine_minutes_charge_full_hour(minutes: int) -> None:
    result = calculate_overtime_amount(
        hourly_price_amount=Decimal("100.00"),
        completed_minutes=minutes,
    )

    assert result.amount == Decimal("100.00")


def test_sixty_minutes_fails_closed_until_multi_hour_rule_is_frozen() -> None:
    with pytest.raises(OvertimeMoneyError, match="60 or more"):
        calculate_overtime_amount(
            hourly_price_amount=Decimal("100.00"),
            completed_minutes=60,
        )


@pytest.mark.parametrize("minutes", [-1, True, Decimal("1")])
def test_invalid_minutes_fail_closed(minutes: object) -> None:
    with pytest.raises(OvertimeMoneyError):
        calculate_overtime_amount(
            hourly_price_amount=Decimal("100.00"),
            completed_minutes=minutes,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "price",
    [Decimal("NaN"), Decimal("Infinity")],
)
def test_invalid_hourly_price_fails_closed(price: Decimal) -> None:
    with pytest.raises(OvertimeMoneyError):
        calculate_overtime_amount(
            hourly_price_amount=price,
            completed_minutes=1,
        )
