from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


class PricingSnapshotUnavailable(Exception):
    """Raised when a trusted pricing snapshot cannot be produced."""


@dataclass(frozen=True)
class PricingSnapshotRequest:
    tenant_id: UUID
    unit_id: UUID
    resource_id: UUID
    resource_category_id: UUID
    professional_id: UUID
    starts_at: datetime
    ends_at: datetime


class PricingSnapshotProducer(Protocol):
    """Contract implemented by the BCOS pricing engine."""

    async def produce(
        self,
        request: PricingSnapshotRequest,
    ) -> dict[str, Any]:
        """Produce the immutable server-side pricing snapshot."""
        ...


class UnconfiguredPricingSnapshotProducer:
    """Fail-closed producer used until BCOS-M6 Pricing is configured."""

    async def produce(
        self,
        request: PricingSnapshotRequest,
    ) -> dict[str, Any]:
        """Reject booking creation while pricing is unavailable."""

        del request

        raise PricingSnapshotUnavailable(
            "Trusted pricing snapshot production is not configured."
        )
