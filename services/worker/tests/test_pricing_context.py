from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID

import pytest

from bcos_worker.pricing_context import (
    PricingContextError,
    hydrate_usage_pricing_context,
)


class FakeMappingResult:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row

    def mappings(self) -> FakeMappingResult:
        return self

    def one_or_none(self) -> dict[str, Any] | None:
        return self._row


class FakeSession:
    def __init__(self, rows: list[dict[str, Any] | None]) -> None:
        self._rows = list(rows)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute(
        self,
        statement: Any,
        params: dict[str, Any],
    ) -> FakeMappingResult:
        self.calls.append((str(statement), params))

        if not self._rows:
            raise AssertionError("unexpected execute call")

        return FakeMappingResult(self._rows.pop(0))


TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
USAGE_ID = UUID("22222222-2222-2222-2222-222222222222")
BOOKING_ID = UUID("33333333-3333-3333-3333-333333333333")
RESOURCE_ID = UUID("44444444-4444-4444-4444-444444444444")
PROFESSIONAL_ID = UUID("55555555-5555-5555-5555-555555555555")
UNIT_ID = UUID("66666666-6666-6666-6666-666666666666")


def usage_row() -> dict[str, Any]:
    return {
        "usage_id": USAGE_ID,
        "tenant_id": TENANT_ID,
        "booking_id": BOOKING_ID,
        "resource_id": RESOURCE_ID,
        "professional_id": PROFESSIONAL_ID,
        "usage_status": "COMPLETED",
        "checked_in_at": datetime(2026, 9, 7, 14, 0, tzinfo=UTC),
        "checked_out_at": datetime(2026, 9, 7, 16, 30, tzinfo=UTC),
        "unit_id": UNIT_ID,
        "booking_starts_at": datetime(2026, 9, 7, 14, 0, tzinfo=UTC),
        "booking_ends_at": datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
        "pricing_snapshot": {
            "pricing_rule": {
                "rule_definition": {
                    "schema_version": 1,
                    "modality": "HOURLY",
                }
            }
        },
        "unit_timezone": "America/Sao_Paulo",
    }


def reception_row() -> dict[str, Any]:
    return {
        "day_of_week": 0,
        "opens_at": time(8, 0),
        "closes_at": time(18, 0),
        "is_closed": False,
    }


@pytest.mark.asyncio
async def test_hydrates_authoritative_tenant_safe_context() -> None:
    session = FakeSession([usage_row(), reception_row()])

    context = await hydrate_usage_pricing_context(
        session,  # type: ignore[arg-type]
        tenant_id=TENANT_ID,
        usage_id=USAGE_ID,
    )

    assert context.tenant_id == TENANT_ID
    assert context.usage_id == USAGE_ID
    assert context.booking_id == BOOKING_ID
    assert context.resource_id == RESOURCE_ID
    assert context.professional_id == PROFESSIONAL_ID
    assert context.unit_id == UNIT_ID
    assert context.usage_status == "COMPLETED"
    assert context.unit_timezone == "America/Sao_Paulo"
    assert context.local_checked_out_at.hour == 13
    assert context.local_checked_out_at.weekday() == 0
    assert context.reception_hours.day_of_week == 0
    assert context.reception_hours.closes_at == time(18, 0)


@pytest.mark.asyncio
async def test_primary_query_is_scoped_by_usage_and_tenant() -> None:
    session = FakeSession([usage_row(), reception_row()])

    await hydrate_usage_pricing_context(
        session,  # type: ignore[arg-type]
        tenant_id=TENANT_ID,
        usage_id=USAGE_ID,
    )

    sql, params = session.calls[0]

    assert "u.id = :usage_id" in sql
    assert "u.tenant_id = :tenant_id" in sql
    assert "b.tenant_id = u.tenant_id" in sql
    assert "un.tenant_id = u.tenant_id" in sql
    assert params == {
        "usage_id": USAGE_ID,
        "tenant_id": TENANT_ID,
    }


@pytest.mark.asyncio
async def test_reception_query_is_tenant_unit_and_local_day_scoped() -> None:
    session = FakeSession([usage_row(), reception_row()])

    await hydrate_usage_pricing_context(
        session,  # type: ignore[arg-type]
        tenant_id=TENANT_ID,
        usage_id=USAGE_ID,
    )

    sql, params = session.calls[1]

    assert "rh.tenant_id = :tenant_id" in sql
    assert "rh.unit_id = :unit_id" in sql
    assert "rh.day_of_week = :day_of_week" in sql
    assert params == {
        "tenant_id": TENANT_ID,
        "unit_id": UNIT_ID,
        "day_of_week": 0,
    }


@pytest.mark.asyncio
async def test_missing_usage_context_fails_closed() -> None:
    session = FakeSession([None])

    with pytest.raises(
        PricingContextError,
        match="pricing context not found",
    ):
        await hydrate_usage_pricing_context(
            session,  # type: ignore[arg-type]
            tenant_id=TENANT_ID,
            usage_id=USAGE_ID,
        )


@pytest.mark.asyncio
async def test_non_completed_usage_fails_closed() -> None:
    row = usage_row()
    row["usage_status"] = "CHECKED_IN"
    session = FakeSession([row])

    with pytest.raises(
        PricingContextError,
        match="usage must be COMPLETED",
    ):
        await hydrate_usage_pricing_context(
            session,  # type: ignore[arg-type]
            tenant_id=TENANT_ID,
            usage_id=USAGE_ID,
        )


@pytest.mark.asyncio
async def test_completed_usage_without_checkout_fails_closed() -> None:
    row = usage_row()
    row["checked_out_at"] = None
    session = FakeSession([row])

    with pytest.raises(
        PricingContextError,
        match="must have checked_in_at and checked_out_at",
    ):
        await hydrate_usage_pricing_context(
            session,  # type: ignore[arg-type]
            tenant_id=TENANT_ID,
            usage_id=USAGE_ID,
        )


@pytest.mark.asyncio
async def test_invalid_pricing_snapshot_fails_closed() -> None:
    row = usage_row()
    row["pricing_snapshot"] = []
    session = FakeSession([row])

    with pytest.raises(
        PricingContextError,
        match="pricing_snapshot must be an object",
    ):
        await hydrate_usage_pricing_context(
            session,  # type: ignore[arg-type]
            tenant_id=TENANT_ID,
            usage_id=USAGE_ID,
        )


@pytest.mark.asyncio
async def test_invalid_unit_timezone_fails_closed() -> None:
    row = usage_row()
    row["unit_timezone"] = "Not/A_Timezone"
    session = FakeSession([row])

    with pytest.raises(
        PricingContextError,
        match="valid IANA timezone",
    ):
        await hydrate_usage_pricing_context(
            session,  # type: ignore[arg-type]
            tenant_id=TENANT_ID,
            usage_id=USAGE_ID,
        )


@pytest.mark.asyncio
async def test_missing_reception_hours_fails_closed() -> None:
    session = FakeSession([usage_row(), None])

    with pytest.raises(
        PricingContextError,
        match="reception hours configuration missing",
    ):
        await hydrate_usage_pricing_context(
            session,  # type: ignore[arg-type]
            tenant_id=TENANT_ID,
            usage_id=USAGE_ID,
        )


@pytest.mark.asyncio
async def test_local_checkout_day_uses_unit_timezone() -> None:
    row = usage_row()
    row["checked_out_at"] = datetime(2026, 9, 7, 1, 30, tzinfo=UTC)

    local_day = 6
    reception = reception_row()
    reception["day_of_week"] = local_day

    session = FakeSession([row, reception])

    context = await hydrate_usage_pricing_context(
        session,  # type: ignore[arg-type]
        tenant_id=TENANT_ID,
        usage_id=USAGE_ID,
    )

    assert context.local_checked_out_at == datetime(
        2026,
        9,
        6,
        22,
        30,
        tzinfo=context.local_checked_out_at.tzinfo,
    )
    assert context.local_checked_out_at.weekday() == local_day
    assert session.calls[1][1]["day_of_week"] == local_day


@pytest.mark.asyncio
async def test_pricing_snapshot_is_copied() -> None:
    row = usage_row()
    original_snapshot = row["pricing_snapshot"]
    session = FakeSession([row, reception_row()])

    context = await hydrate_usage_pricing_context(
        session,  # type: ignore[arg-type]
        tenant_id=TENANT_ID,
        usage_id=USAGE_ID,
    )

    assert context.pricing_snapshot == original_snapshot
    assert context.pricing_snapshot is not original_snapshot
