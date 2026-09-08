"""Trusted pricing snapshot production for BCOS bookings."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.bookings.pricing import (
    PricingSnapshotProducer,
    PricingSnapshotRequest,
    PricingSnapshotUnavailable,
)
from bcos_api.pricing.repository import resolve_pricing_rule


class DatabasePricingSnapshotProducer(PricingSnapshotProducer):
    """Resolve and freeze the trusted pricing rule for a booking."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def produce(
        self,
        request: PricingSnapshotRequest,
    ) -> dict[str, Any]:
        """Produce an immutable snapshot without performing billing calculations."""

        rule = await resolve_pricing_rule(
            self._session,
            tenant_id=request.tenant_id,
            unit_id=request.unit_id,
            resource_category_id=request.resource_category_id,
            effective_at=request.starts_at,
        )

        if rule is None:
            raise PricingSnapshotUnavailable(
                "No active pricing rule is configured for this booking."
            )

        return {
            "schema_version": 1,
            "pricing_rule": {
                "id": str(rule.id),
                "name": rule.name,
                "priority": rule.priority,
                "currency": rule.currency,
                "unit_id": str(rule.unit_id) if rule.unit_id is not None else None,
                "resource_category_id": (
                    str(rule.resource_category_id)
                    if rule.resource_category_id is not None
                    else None
                ),
                "rule_definition": deepcopy(rule.rule_definition),
                "valid_from": (
                    rule.valid_from.isoformat()
                    if rule.valid_from is not None
                    else None
                ),
                "valid_until": (
                    rule.valid_until.isoformat()
                    if rule.valid_until is not None
                    else None
                ),
            },
            "booking_context": {
                "unit_id": str(request.unit_id),
                "resource_id": str(request.resource_id),
                "resource_category_id": str(request.resource_category_id),
                "professional_id": str(request.professional_id),
                "starts_at": request.starts_at.isoformat(),
                "ends_at": request.ends_at.isoformat(),
            },
        }
