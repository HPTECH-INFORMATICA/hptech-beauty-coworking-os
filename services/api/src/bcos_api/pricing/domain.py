from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID


class InvalidPricingRule(ValueError):
    """Raised when a pricing rule violates the frozen BCOS contract."""


class PricingRuleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass(frozen=True)
class PricingRule:
    id: UUID
    tenant_id: UUID
    unit_id: UUID | None
    resource_category_id: UUID | None
    name: str
    status: PricingRuleStatus
    priority: int
    currency: Literal["BRL"]
    rule_definition: dict[str, Any]
    valid_from: datetime | None
    valid_until: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


def _require_aware_datetime(
    value: datetime | None,
    *,
    field_name: str,
) -> None:
    if value is None:
        return

    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidPricingRule(
            f"{field_name} must be timezone-aware when provided."
        )


def _require_decimal_string(value: object, *, field_name: str) -> None:
    from decimal import Decimal, InvalidOperation

    if not isinstance(value, str):
        raise InvalidPricingRule(f"{field_name} must be a decimal string.")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise InvalidPricingRule(f"{field_name} must be a valid decimal string.") from exc
    if not amount.is_finite() or amount < 0:
        raise InvalidPricingRule(f"{field_name} must be a non-negative finite decimal.")


def validate_pricing_rule_definition(
    *,
    name: str,
    priority: int,
    currency: Literal["BRL"],
    rule_definition: dict[str, Any],
    valid_from: datetime | None,
    valid_until: datetime | None,
) -> None:
    """Validate the HUMAN APPROVED M7-A3-T9 Pricing Rule Definition V1."""

    if not name.strip():
        raise InvalidPricingRule("Pricing rule name must not be blank.")
    if priority < 0:
        raise InvalidPricingRule("Pricing rule priority must be greater than or equal to zero.")
    if currency != "BRL":
        raise InvalidPricingRule("Pricing rule currency must be BRL.")
    if not isinstance(rule_definition, dict):
        raise InvalidPricingRule("Pricing rule definition must be an object.")

    required = {"schema_version", "modality", "base_price_amount", "overtime"}
    missing = required.difference(rule_definition)
    if missing:
        raise InvalidPricingRule(
            "Pricing rule definition is missing required fields: "
            + ", ".join(sorted(missing))
        )
    if rule_definition["schema_version"] != 1:
        raise InvalidPricingRule("Pricing rule schema_version must be 1.")
    if rule_definition["modality"] not in {"HOURLY", "PERIOD", "WEEKLY", "MONTHLY"}:
        raise InvalidPricingRule("Pricing rule modality is unsupported.")

    _require_decimal_string(rule_definition["base_price_amount"], field_name="base_price_amount")

    overtime = rule_definition["overtime"]
    if not isinstance(overtime, dict):
        raise InvalidPricingRule("Pricing rule overtime must be an object.")
    overtime_required = {
        "hourly_price_amount",
        "proportional_until_minutes",
        "full_hour_from_minutes",
        "forgiveness_allowed",
    }
    if overtime_required.difference(overtime):
        raise InvalidPricingRule("Pricing rule overtime is missing required fields.")
    _require_decimal_string(overtime["hourly_price_amount"], field_name="overtime.hourly_price_amount")
    if not isinstance(overtime["proportional_until_minutes"], int) or isinstance(overtime["proportional_until_minutes"], bool) or overtime["proportional_until_minutes"] < 0:
        raise InvalidPricingRule("overtime.proportional_until_minutes must be a non-negative integer.")
    if not isinstance(overtime["full_hour_from_minutes"], int) or isinstance(overtime["full_hour_from_minutes"], bool) or overtime["full_hour_from_minutes"] <= 0:
        raise InvalidPricingRule("overtime.full_hour_from_minutes must be a positive integer.")
    if overtime["proportional_until_minutes"] >= overtime["full_hour_from_minutes"]:
        raise InvalidPricingRule("overtime proportional threshold must precede full-hour threshold.")
    if not isinstance(overtime["forgiveness_allowed"], bool):
        raise InvalidPricingRule("overtime.forgiveness_allowed must be boolean.")

    penalty = rule_definition.get("conflict_penalty")
    if penalty is not None:
        if not isinstance(penalty, dict) or penalty.get("mode") not in {"FIXED_AMOUNT", "PERCENTAGE"}:
            raise InvalidPricingRule("conflict_penalty mode is unsupported.")
        _require_decimal_string(penalty.get("value"), field_name="conflict_penalty.value")

    _require_aware_datetime(valid_from, field_name="valid_from")
    _require_aware_datetime(valid_until, field_name="valid_until")
    if valid_from is not None and valid_until is not None and valid_until <= valid_from:
        raise InvalidPricingRule("valid_until must be later than valid_from.")
