"""Unit tests for BCOS Outbox repository operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from bcos_worker.outbox import OutboxEvent, OutboxStatus
from bcos_worker.outbox_repository import (
    claim_next_event,
    mark_event_processed,
)


class FakeMappingsResult:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row

    def mappings(self) -> "FakeMappingsResult":
        return self

    def one_or_none(self) -> dict[str, Any] | None:
        return self._row


class FakeScalarResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value


class FakeSession:
    def __init__(self, results: list[object]) -> None:
        self._results = results
        self.calls: list[tuple[object, dict[str, object] | None]] = []

    async def execute(
        self,
        statement: object,
        params: dict[str, object] | None = None,
    ) -> object:
        self.calls.append((statement, params))
        return self._results.pop(0)


def make_claim_row() -> dict[str, Any]:
    now = datetime.now(UTC)

    return {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "dedupe_key": f"usage-completed:{uuid4()}",
        "event_type": "USAGE_COMPLETED",
        "aggregate_type": "USAGE",
        "aggregate_id": uuid4(),
        "payload": {
            "usage_id": str(uuid4()),
            "checked_out_at": now.isoformat(),
        },
        "status": "PROCESSING",
        "attempts": 1,
        "available_at": now,
        "processed_at": None,
        "last_error": None,
        "created_at": now,
    }


@pytest.mark.asyncio
async def test_claim_next_event_returns_none_when_no_event() -> None:
    session = FakeSession([FakeMappingsResult(None)])

    event = await claim_next_event(session)  # type: ignore[arg-type]

    assert event is None
    assert len(session.calls) == 1


@pytest.mark.asyncio
async def test_claim_next_event_maps_claimed_event() -> None:
    row = make_claim_row()
    session = FakeSession([FakeMappingsResult(row)])

    event = await claim_next_event(session)  # type: ignore[arg-type]

    assert isinstance(event, OutboxEvent)
    assert event.id == row["id"]
    assert event.tenant_id == row["tenant_id"]
    assert event.status is OutboxStatus.PROCESSING
    assert event.attempts == 1
    assert event.payload == row["payload"]


@pytest.mark.asyncio
async def test_claim_query_contains_approved_locking_contract() -> None:
    session = FakeSession([FakeMappingsResult(None)])

    await claim_next_event(session)  # type: ignore[arg-type]

    statement = str(session.calls[0][0])

    assert "status = 'PENDING'" in statement
    assert "available_at <= now()" in statement
    assert "ORDER BY available_at, created_at" in statement
    assert "FOR UPDATE SKIP LOCKED" in statement
    assert "status = 'PROCESSING'" in statement
    assert "attempts = oe.attempts + 1" in statement


@pytest.mark.asyncio
async def test_mark_event_processed_requires_processing_state_and_tenant() -> None:
    row = make_claim_row()
    event = OutboxEvent(
        id=row["id"],
        tenant_id=row["tenant_id"],
        dedupe_key=row["dedupe_key"],
        event_type=row["event_type"],
        aggregate_type=row["aggregate_type"],
        aggregate_id=row["aggregate_id"],
        payload=row["payload"],
        status=OutboxStatus.PROCESSING,
        attempts=row["attempts"],
        available_at=row["available_at"],
        processed_at=row["processed_at"],
        last_error=row["last_error"],
        created_at=row["created_at"],
    )
    session = FakeSession([FakeScalarResult(event.id)])

    updated = await mark_event_processed(
        session,  # type: ignore[arg-type]
        event,
    )

    assert updated is True

    statement = str(session.calls[0][0])
    params = session.calls[0][1]

    assert "status = 'PROCESSED'" in statement
    assert "processed_at = now()" in statement
    assert "last_error = NULL" in statement
    assert "tenant_id = :tenant_id" in statement
    assert "status = 'PROCESSING'" in statement
    assert params == {
        "event_id": event.id,
        "tenant_id": event.tenant_id,
    }


@pytest.mark.asyncio
async def test_mark_event_processed_returns_false_when_not_updated() -> None:
    row = make_claim_row()
    event = OutboxEvent(
        id=row["id"],
        tenant_id=row["tenant_id"],
        dedupe_key=row["dedupe_key"],
        event_type=row["event_type"],
        aggregate_type=row["aggregate_type"],
        aggregate_id=row["aggregate_id"],
        payload=row["payload"],
        status=OutboxStatus.PROCESSING,
        attempts=row["attempts"],
        available_at=row["available_at"],
        processed_at=row["processed_at"],
        last_error=row["last_error"],
        created_at=row["created_at"],
    )
    session = FakeSession([FakeScalarResult(None)])

    updated = await mark_event_processed(
        session,  # type: ignore[arg-type]
        event,
    )

    assert updated is False
