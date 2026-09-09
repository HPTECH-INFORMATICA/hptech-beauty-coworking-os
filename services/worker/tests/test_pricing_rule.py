from decimal import Decimal

import pytest

from bcos_worker.pricing_rule import (
    ConflictPenaltyMode,
    PricingModality,
    PricingRuleDefinitionError,
    parse_pricing_rule_definition,
)


def valid_rule() -> dict[str, object]:
    return {
        "schema_version": 1,
        "modality": "HOURLY",
        "base_price_amount": "120.00",
        "overtime": {
            "hourly_price_amount": "120.00",
            "proportional_until_minutes": 29,
            "full_hour_from_minutes": 30,
            "forgiveness_allowed": True,
        },
    }


def test_parse_valid_rule_without_conflict_penalty() -> None:
    rule = parse_pricing_rule_definition(valid_rule())

    assert rule.schema_version == 1
    assert rule.modality is PricingModality.HOURLY
    assert rule.base_price_amount == Decimal("120.00")
    assert rule.overtime.hourly_price_amount == Decimal("120.00")
    assert rule.overtime.proportional_until_minutes == 29
    assert rule.overtime.full_hour_from_minutes == 30
    assert rule.overtime.forgiveness_allowed is True
    assert rule.conflict_penalty is None


@pytest.mark.parametrize(
    "modality",
    ["HOURLY", "PERIOD", "WEEKLY", "MONTHLY"],
)
def test_accepts_all_approved_modalities(modality: str) -> None:
    data = valid_rule()
    data["modality"] = modality

    rule = parse_pricing_rule_definition(data)

    assert rule.modality.value == modality


@pytest.mark.parametrize(
    ("mode", "value"),
    [
        ("FIXED_AMOUNT", "50.00"),
        ("PERCENTAGE", "20"),
    ],
)
def test_parses_approved_conflict_penalty_modes(
    mode: str,
    value: str,
) -> None:
    data = valid_rule()
    data["conflict_penalty"] = {
        "mode": mode,
        "value": value,
    }

    rule = parse_pricing_rule_definition(data)

    assert rule.conflict_penalty is not None
    assert rule.conflict_penalty.mode is ConflictPenaltyMode(mode)
    assert rule.conflict_penalty.value == Decimal(value)


def test_rejects_unsupported_schema_version() -> None:
    data = valid_rule()
    data["schema_version"] = 2

    with pytest.raises(PricingRuleDefinitionError, match="schema_version must be 1"):
        parse_pricing_rule_definition(data)


def test_rejects_unsupported_modality() -> None:
    data = valid_rule()
    data["modality"] = "DAILY"

    with pytest.raises(PricingRuleDefinitionError, match="unsupported modality"):
        parse_pricing_rule_definition(data)


def test_rejects_missing_required_field() -> None:
    data = valid_rule()
    del data["base_price_amount"]

    with pytest.raises(
        PricingRuleDefinitionError,
        match=r"rule_definition\.base_price_amount is required",
    ):
        parse_pricing_rule_definition(data)


def test_rejects_binary_float_for_financial_values() -> None:
    data = valid_rule()
    data["base_price_amount"] = 120.5

    with pytest.raises(
        PricingRuleDefinitionError,
        match="without binary floating point",
    ):
        parse_pricing_rule_definition(data)


def test_rejects_invalid_decimal() -> None:
    data = valid_rule()
    data["base_price_amount"] = "not-money"

    with pytest.raises(
        PricingRuleDefinitionError,
        match="must be a valid decimal value",
    ):
        parse_pricing_rule_definition(data)


def test_rejects_changed_proportional_threshold() -> None:
    data = valid_rule()
    overtime = dict(data["overtime"])
    overtime["proportional_until_minutes"] = 30
    data["overtime"] = overtime

    with pytest.raises(
        PricingRuleDefinitionError,
        match="proportional_until_minutes must be 29",
    ):
        parse_pricing_rule_definition(data)


def test_rejects_changed_full_hour_threshold() -> None:
    data = valid_rule()
    overtime = dict(data["overtime"])
    overtime["full_hour_from_minutes"] = 31
    data["overtime"] = overtime

    with pytest.raises(
        PricingRuleDefinitionError,
        match="full_hour_from_minutes must be 30",
    ):
        parse_pricing_rule_definition(data)


def test_rejects_non_boolean_forgiveness_flag() -> None:
    data = valid_rule()
    overtime = dict(data["overtime"])
    overtime["forgiveness_allowed"] = "yes"
    data["overtime"] = overtime

    with pytest.raises(
        PricingRuleDefinitionError,
        match="forgiveness_allowed must be a boolean",
    ):
        parse_pricing_rule_definition(data)


def test_rejects_unsupported_conflict_penalty_mode() -> None:
    data = valid_rule()
    data["conflict_penalty"] = {
        "mode": "MULTIPLIER",
        "value": "2",
    }

    with pytest.raises(
        PricingRuleDefinitionError,
        match="unsupported conflict_penalty.mode",
    ):
        parse_pricing_rule_definition(data)


def test_preserves_decimal_precision_without_rounding() -> None:
    data = valid_rule()
    data["base_price_amount"] = "123.456789"

    rule = parse_pricing_rule_definition(data)

    assert rule.base_price_amount == Decimal("123.456789")
