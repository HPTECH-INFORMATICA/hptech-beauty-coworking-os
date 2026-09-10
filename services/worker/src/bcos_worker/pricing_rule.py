"""Parser for the HUMAN APPROVED M7-A3-T8/T9 pricing rule contract."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any


class PricingRuleDefinitionError(ValueError):
    """Raised when a frozen V1 pricing rule definition is invalid."""


class PricingModality(StrEnum):
    HOURLY = "HOURLY"
    PERIOD = "PERIOD"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class ConflictPenaltyMode(StrEnum):
    FIXED_AMOUNT = "FIXED_AMOUNT"
    PERCENTAGE = "PERCENTAGE"


@dataclass(frozen=True, slots=True)
class OvertimeRule:
    hourly_price_amount: Decimal
    proportional_until_minutes: int
    full_hour_from_minutes: int
    forgiveness_allowed: bool


@dataclass(frozen=True, slots=True)
class ConflictPenaltyRule:
    mode: ConflictPenaltyMode
    value: Decimal


@dataclass(frozen=True, slots=True)
class PricingRuleDefinitionV1:
    schema_version: int
    modality: PricingModality
    base_price_amount: Decimal
    overtime: OvertimeRule
    conflict_penalty: ConflictPenaltyRule | None


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PricingRuleDefinitionError(f"{field} must be an object")
    return value


def _require_field(data: dict[str, Any], field: str, parent: str) -> Any:
    if field not in data:
        raise PricingRuleDefinitionError(f"{parent}.{field} is required")
    return data[field]


def _parse_decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise PricingRuleDefinitionError(
            f"{field} must be represented without binary floating point"
        )

    if not isinstance(value, (str, int, Decimal)):
        raise PricingRuleDefinitionError(f"{field} must be a decimal value")

    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        raise PricingRuleDefinitionError(f"{field} must be a valid decimal value") from None

    if not parsed.is_finite():
        raise PricingRuleDefinitionError(f"{field} must be finite")

    return parsed


def _parse_modality(value: Any) -> PricingModality:
    if not isinstance(value, str):
        raise PricingRuleDefinitionError("modality must be a string")

    try:
        return PricingModality(value)
    except ValueError:
        raise PricingRuleDefinitionError(f"unsupported modality: {value}") from None


def _parse_overtime(value: Any) -> OvertimeRule:
    data = _require_mapping(value, "overtime")

    hourly_price_amount = _parse_decimal(
        _require_field(data, "hourly_price_amount", "overtime"),
        "overtime.hourly_price_amount",
    )

    proportional = _require_field(
        data,
        "proportional_until_minutes",
        "overtime",
    )
    if isinstance(proportional, bool) or not isinstance(proportional, int):
        raise PricingRuleDefinitionError(
            "overtime.proportional_until_minutes must be an integer"
        )

    full_hour = _require_field(
        data,
        "full_hour_from_minutes",
        "overtime",
    )
    if isinstance(full_hour, bool) or not isinstance(full_hour, int):
        raise PricingRuleDefinitionError(
            "overtime.full_hour_from_minutes must be an integer"
        )

    forgiveness = _require_field(
        data,
        "forgiveness_allowed",
        "overtime",
    )
    if not isinstance(forgiveness, bool):
        raise PricingRuleDefinitionError(
            "overtime.forgiveness_allowed must be a boolean"
        )

    return OvertimeRule(
        hourly_price_amount=hourly_price_amount,
        proportional_until_minutes=proportional,
        full_hour_from_minutes=full_hour,
        forgiveness_allowed=forgiveness,
    )


def _parse_conflict_penalty(value: Any) -> ConflictPenaltyRule:
    data = _require_mapping(value, "conflict_penalty")

    raw_mode = _require_field(data, "mode", "conflict_penalty")
    if not isinstance(raw_mode, str):
        raise PricingRuleDefinitionError("conflict_penalty.mode must be a string")

    try:
        mode = ConflictPenaltyMode(raw_mode)
    except ValueError:
        raise PricingRuleDefinitionError(
            f"unsupported conflict_penalty.mode: {raw_mode}"
        ) from None

    penalty_value = _parse_decimal(
        _require_field(data, "value", "conflict_penalty"),
        "conflict_penalty.value",
    )

    return ConflictPenaltyRule(
        mode=mode,
        value=penalty_value,
    )


def parse_pricing_rule_definition(value: Any) -> PricingRuleDefinitionV1:
    """Parse the frozen V1 rule_definition without performing pricing calculations."""
    data = _require_mapping(value, "rule_definition")

    schema_version = _require_field(data, "schema_version", "rule_definition")
    if isinstance(schema_version, bool) or schema_version != 1:
        raise PricingRuleDefinitionError("schema_version must be 1")

    modality = _parse_modality(
        _require_field(data, "modality", "rule_definition")
    )

    base_price_amount = _parse_decimal(
        _require_field(data, "base_price_amount", "rule_definition"),
        "base_price_amount",
    )

    overtime = _parse_overtime(
        _require_field(data, "overtime", "rule_definition")
    )

    raw_penalty = data.get("conflict_penalty")
    conflict_penalty = (
        None
        if raw_penalty is None
        else _parse_conflict_penalty(raw_penalty)
    )

    return PricingRuleDefinitionV1(
        schema_version=1,
        modality=modality,
        base_price_amount=base_price_amount,
        overtime=overtime,
        conflict_penalty=conflict_penalty,
    )
