from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bcos_api.bookings.pricing import (
    PricingSnapshotRequest,
    PricingSnapshotUnavailable,
)
from bcos_api.pricing.domain import PricingRule, PricingRuleStatus
from bcos_api.pricing.snapshot import DatabasePricingSnapshotProducer


@pytest.mark.asyncio
async def test_produce_freezes_resolved_pricing_rule(monkeypatch) -> None:
    tenant_id = uuid4()
    unit_id = uuid4()
    resource_id = uuid4()
    resource_category_id = uuid4()
    professional_id = uuid4()
    rule_id = uuid4()

    starts_at = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
    ends_at = datetime(2026, 9, 8, 13, 0, tzinfo=UTC)

    rule_definition = {
        "opaque_contract": {
            "mode": "configured",
        }
    }

    rule = PricingRule(
        id=rule_id,
        tenant_id=tenant_id,
        unit_id=unit_id,
        resource_category_id=resource_category_id,
        name="Regra principal",
        status=PricingRuleStatus.ACTIVE,
        priority=10,
        currency="BRL",
        rule_definition=rule_definition,
        valid_from=None,
        valid_until=None,
        created_at=starts_at,
        updated_at=starts_at,
        deleted_at=None,
    )

    calls: list[dict[str, object]] = []

    async def fake_resolve_pricing_rule(
        session,
        *,
        tenant_id,
        unit_id,
        resource_category_id,
        effective_at,
    ):
        calls.append(
            {
                "session": session,
                "tenant_id": tenant_id,
                "unit_id": unit_id,
                "resource_category_id": resource_category_id,
                "effective_at": effective_at,
            }
        )
        return rule

    monkeypatch.setattr(
        "bcos_api.pricing.snapshot.resolve_pricing_rule",
        fake_resolve_pricing_rule,
    )

    session = object()
    producer = DatabasePricingSnapshotProducer(session)  # type: ignore[arg-type]

    request = PricingSnapshotRequest(
        tenant_id=tenant_id,
        unit_id=unit_id,
        resource_id=resource_id,
        resource_category_id=resource_category_id,
        professional_id=professional_id,
        starts_at=starts_at,
        ends_at=ends_at,
    )

    snapshot = await producer.produce(request)

    assert calls == [
        {
            "session": session,
            "tenant_id": tenant_id,
            "unit_id": unit_id,
            "resource_category_id": resource_category_id,
            "effective_at": starts_at,
        }
    ]

    assert snapshot["schema_version"] == 1
    assert snapshot["pricing_rule"] == {
        "id": str(rule_id),
        "name": "Regra principal",
        "priority": 10,
        "currency": "BRL",
        "unit_id": str(unit_id),
        "resource_category_id": str(resource_category_id),
        "rule_definition": rule_definition,
        "valid_from": None,
        "valid_until": None,
    }
    assert snapshot["booking_context"] == {
        "unit_id": str(unit_id),
        "resource_id": str(resource_id),
        "resource_category_id": str(resource_category_id),
        "professional_id": str(professional_id),
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
    }

    assert snapshot["pricing_rule"]["rule_definition"] is not rule_definition


@pytest.mark.asyncio
async def test_produce_fails_closed_when_no_rule_is_resolved(monkeypatch) -> None:
    async def fake_resolve_pricing_rule(
        session,
        *,
        tenant_id,
        unit_id,
        resource_category_id,
        effective_at,
    ):
        return None

    monkeypatch.setattr(
        "bcos_api.pricing.snapshot.resolve_pricing_rule",
        fake_resolve_pricing_rule,
    )

    producer = DatabasePricingSnapshotProducer(object())  # type: ignore[arg-type]

    request = PricingSnapshotRequest(
        tenant_id=uuid4(),
        unit_id=uuid4(),
        resource_id=uuid4(),
        resource_category_id=uuid4(),
        professional_id=uuid4(),
        starts_at=datetime(2026, 9, 8, 12, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 8, 13, 0, tzinfo=UTC),
    )

    with pytest.raises(
        PricingSnapshotUnavailable,
        match="No active pricing rule is configured",
    ):
        await producer.produce(request)
