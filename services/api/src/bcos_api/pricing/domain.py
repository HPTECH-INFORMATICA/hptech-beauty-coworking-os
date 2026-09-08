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


def validate_pricing_rule_definition(
    *,
    name: str,
    priority: int,
    currency: Literal["BRL"],
    rule_definition: dict[str, Any],
    valid_from: datetime | None,
    valid_until: datetime | None,
) -> None:
    """Validate only semantics frozen by schema/OpenAPI.

    rule_definition intentionally remains open in BCOS-M6. Financial
    calculation semantics are not inferred or invented here.
    """

    if not name.strip():
        raise InvalidPricingRule("Pricing rule name must not be blank.")

    if priority < 0:
        raise InvalidPricingRule(
            "Pricing rule priority must be greater than or equal to zero."
        )

    if currency != "BRL":
        raise InvalidPricingRule("Pricing rule currency must be BRL.")

    if not isinstance(rule_definition, dict):
        raise InvalidPricingRule(
            "Pricing rule definition must be an object."
        )

    _require_aware_datetime(valid_from, field_name="valid_from")
    _require_aware_datetime(valid_until, field_name="valid_until")

    if (
        valid_from is not None
        and valid_until is not None
        and valid_until <= valid_from
    ):
        raise InvalidPricingRule(
            "valid_until must be later than valid_from."
        )
