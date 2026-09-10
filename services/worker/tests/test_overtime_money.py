from decimal import Decimal

import pytest

from bcos_worker.overtime_money import (
    OvertimeMoneyError,
    calculate_overtime_amount,
    quantize_money,
)


def calculate(minutes: int) -> Decimal:
    return calculate_overtime_amount(
        hourly_price_amount=Decimal("100.00"),
        completed_minutes=minutes,
        proportional_until_minutes=29,
        full_hour_from_minutes=30,
    ).amount


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [
        (0, Decimal("0.00")),
        (1, Decimal("1.67")),
        (29, Decimal("48.33")),
        (30, Decimal("100.00")),
        (59, Decimal("100.00")),
        (60, Decimal("100.00")),
        (61, Decimal("101.67")),
        (89, Decimal("148.33")),
        (90, Decimal("200.00")),
        (119, Decimal("200.00")),
        (120, Decimal("200.00")),
        (149, Decimal("248.33")),
        (150, Decimal("300.00")),
    ],
)
def test_configured_29_30_rule_across_multiple_hours(
    minutes: int,
    expected: Decimal,
) -> None:
    assert calculate(minutes) == expected


def test_worker_honors_different_coworking_threshold() -> None:
    result = calculate_overtime_amount(
        hourly_price_amount=Decimal("120.00"),
        completed_minutes=20,
        proportional_until_minutes=14,
        full_hour_from_minutes=15,
    )

    assert result.amount == Decimal("120.00")


def test_worker_honors_different_coworking_proportional_window() -> None:
    result = calculate_overtime_amount(
        hourly_price_amount=Decimal("120.00"),
        completed_minutes=14,
        proportional_until_minutes=14,
        full_hour_from_minutes=15,
    )

    assert result.amount == Decimal("28.00")


def test_multi_hour_uses_same_configured_remainder_rule() -> None:
    result = calculate_overtime_amount(
        hourly_price_amount=Decimal("120.00"),
        completed_minutes=74,
        proportional_until_minutes=14,
        full_hour_from_minutes=15,
    )

    assert result.amount == Decimal("148.00")


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


def test_gap_in_configured_rule_fails_closed() -> None:
    with pytest.raises(OvertimeMoneyError, match="not covered"):
        calculate_overtime_amount(
            hourly_price_amount=Decimal("100.00"),
            completed_minutes=20,
            proportional_until_minutes=10,
            full_hour_from_minutes=30,
        )


@pytest.mark.parametrize("minutes", [-1, True, Decimal("1")])
def test_invalid_completed_minutes_fail_closed(minutes: object) -> None:
    with pytest.raises(OvertimeMoneyError):
        calculate_overtime_amount(
            hourly_price_amount=Decimal("100.00"),
            completed_minutes=minutes,  # type: ignore[arg-type]
            proportional_until_minutes=29,
            full_hour_from_minutes=30,
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
            proportional_until_minutes=29,
            full_hour_from_minutes=30,
        )
