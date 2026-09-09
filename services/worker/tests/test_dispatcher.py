"""Unit tests for the BCOS Outbox dispatcher contract."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bcos_worker.dispatcher import (
    InvalidOutboxPayloadError,
    UnsupportedOutboxEventError,
    UsageCompletedEvent,
    dispatch_event,
    parse_usage_completed,
)
from bcos_worker.outbox import OutboxEvent, OutboxStatus


def make_event(
    *,
    event_type: str = "USAGE_COMPLETED",
    payload: dict[str, object] | None = None,
) -> OutboxEvent:
    now = datetime.now(UTC)
    usage_id = uuid4()

    return OutboxEvent(
        id=uuid4(),
        tenant_id=uuid4(),
        dedupe_key=f"usage-completed:{usage_id}",
        event_type=event_type,
        aggregate_type="USAGE",
        aggregate_id=usage_id,
        payload=payload
        or {
            "usage_id": str(usage_id),
            "checked_out_at": now.isoformat(),
        },
        status=OutboxStatus.PROCESSING,
        attempts=1,
        available_at=now,
        processing_started_at=now,
        processed_at=None,
        last_error=None,
        created_at=now,
    )


def test_parse_usage_completed_accepts_frozen_payload() -> None:
    event = make_event()

    parsed = parse_usage_completed(event)

    assert isinstance(parsed, UsageCompletedEvent)
    assert parsed.usage_id == event.aggregate_id
    assert parsed.checked_out_at.tzinfo is not None


def test_parse_usage_completed_rejects_unknown_event_type() -> None:
    event = make_event(event_type="UNKNOWN_EVENT")

    with pytest.raises(UnsupportedOutboxEventError):
        parse_usage_completed(event)


@pytest.mark.parametrize(
    "payload",
    [
        {"checked_out_at": datetime.now(UTC).isoformat()},
        {"usage_id": str(uuid4())},
        {
            "usage_id": "not-a-uuid",
            "checked_out_at": datetime.now(UTC).isoformat(),
        },
        {
            "usage_id": str(uuid4()),
            "checked_out_at": "not-a-datetime",
        },
    ],
)
def test_parse_usage_completed_rejects_invalid_payload(
    payload: dict[str, object],
) -> None:
    event = make_event(payload=payload)

    with pytest.raises(InvalidOutboxPayloadError):
        parse_usage_completed(event)


def test_parse_usage_completed_requires_timezone() -> None:
    event = make_event(
        payload={
            "usage_id": str(uuid4()),
            "checked_out_at": "2026-09-09T12:30:00",
        }
    )

    with pytest.raises(InvalidOutboxPayloadError):
        parse_usage_completed(event)


@pytest.mark.asyncio
async def test_dispatch_event_calls_usage_completed_handler() -> None:
    event = make_event()
    received: list[tuple[OutboxEvent, UsageCompletedEvent]] = []

    async def handler(
        received_event: OutboxEvent,
        usage_completed: UsageCompletedEvent,
    ) -> None:
        received.append((received_event, usage_completed))

    await dispatch_event(event, handler)

    assert len(received) == 1
    assert received[0][0] is event
    assert received[0][1].usage_id == event.aggregate_id

