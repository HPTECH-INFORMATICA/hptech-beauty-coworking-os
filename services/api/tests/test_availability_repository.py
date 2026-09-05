"""Permanent M3 tests for the BCOS Availability repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from bcos_api.availability.domain import Availability
from bcos_api.availability.repository import list_resource_availability


class FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> FakeMappings:
        return FakeMappings(self._rows)


class FakeSession:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.statement = ""
        self.parameters: dict[str, Any] = {}

    async def execute(
        self,
        statement: Any,
        parameters: dict[str, Any],
    ) -> FakeResult:
        self.statement = str(statement)
        self.parameters = parameters
        return FakeResult(self._rows)


@pytest.mark.asyncio
async def test_repository_uses_canonical_occupancy_semantics() -> None:
    tenant_id = uuid4()
    unit_id = uuid4()
    resource_id = uuid4()
    category_id = uuid4()
    starts_at = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
    ends_at = datetime(2026, 9, 5, 13, 0, tzinfo=UTC)

    session = FakeSession(
        [
            {
                "resource_id": resource_id,
                "available": False,
                "reason": "MANUAL_BLOCK",
            }
        ]
    )

    result = await list_resource_availability(
        session,  # type: ignore[arg-type]
        tenant_id=tenant_id,
        unit_id=unit_id,
        starts_at=starts_at,
        ends_at=ends_at,
        resource_id=resource_id,
        category_id=category_id,
    )

    normalized_sql = " ".join(session.statement.split())

    assert "FROM resources r" in normalized_sql
    assert "FROM resource_occupancies ro" in normalized_sql
    assert "ro.tenant_id = r.tenant_id" in normalized_sql
    assert "ro.resource_id = r.id" in normalized_sql
    assert "ro.status = 'ACTIVE'" in normalized_sql
    assert "ro.period && tstzrange(" in normalized_sql
    assert "'[)'" in normalized_sql
    assert "r.tenant_id = :tenant_id" in normalized_sql
    assert "r.unit_id = :unit_id" in normalized_sql
    assert "r.deleted_at IS NULL" in normalized_sql
    assert "r.active = true" in normalized_sql
    assert "(:resource_id IS NULL OR r.id = :resource_id)" in normalized_sql
    assert (
        "(:category_id IS NULL OR r.category_id = :category_id)"
        in normalized_sql
    )
    assert "SELECT ro.source_type::text" in normalized_sql

    assert session.parameters == {
        "tenant_id": tenant_id,
        "unit_id": unit_id,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "resource_id": resource_id,
        "category_id": category_id,
    }

    assert result == [
        Availability(
            resource_id=resource_id,
            available=False,
            reason="MANUAL_BLOCK",
        )
    ]


@pytest.mark.asyncio
async def test_repository_maps_available_resource_without_reason() -> None:
    resource_id = uuid4()

    session = FakeSession(
        [
            {
                "resource_id": resource_id,
                "available": True,
                "reason": None,
            }
        ]
    )

    starts_at = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
    ends_at = datetime(2026, 9, 5, 13, 0, tzinfo=UTC)

    result = await list_resource_availability(
        session,  # type: ignore[arg-type]
        tenant_id=uuid4(),
        unit_id=uuid4(),
        starts_at=starts_at,
        ends_at=ends_at,
    )

    assert session.parameters["resource_id"] is None
    assert session.parameters["category_id"] is None
    assert result == [
        Availability(
            resource_id=resource_id,
            available=True,
            reason=None,
        )
    ]


@pytest.mark.asyncio
async def test_repository_preserves_multiple_resource_results() -> None:
    first_resource_id = uuid4()
    second_resource_id = uuid4()

    session = FakeSession(
        [
            {
                "resource_id": first_resource_id,
                "available": True,
                "reason": None,
            },
            {
                "resource_id": second_resource_id,
                "available": False,
                "reason": "CLEANING",
            },
        ]
    )

    result = await list_resource_availability(
        session,  # type: ignore[arg-type]
        tenant_id=uuid4(),
        unit_id=uuid4(),
        starts_at=datetime(2026, 9, 5, 12, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 5, 13, 0, tzinfo=UTC),
    )

    assert result == [
        Availability(
            resource_id=first_resource_id,
            available=True,
            reason=None,
        ),
        Availability(
            resource_id=second_resource_id,
            available=False,
            reason="CLEANING",
        ),
    ]

