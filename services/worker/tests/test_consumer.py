"""Unit tests for the approved BCOS consumer execution lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from bcos_worker.consumer import (
    ConsumerIterationResult,
    process_one,
)
from bcos_worker.dispatcher import UsageCompletedEvent
from bcos_worker.outbox import OutboxEvent, OutboxStatus


def make_event() -> OutboxEvent:
    now = datetime.now(UTC)
    usage_id = uuid4()

    return OutboxEvent(
        id=uuid4(),
        tenant_id=uuid4(),
        dedupe_key=f"usage-completed:{usage_id}",
        event_type="USAGE_COMPLETED",
        aggregate_type="USAGE",
        aggregate_id=usage_id,
        payload={
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


class FakeTransaction:
    def __init__(self, session: "FakeSession") -> None:
        self._session = session

    async def __aenter__(self) -> None:
        self._session.events.append("transaction_begin")

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        if exc_type is None:
            self._session.events.append("commit")
        else:
            self._session.events.append("rollback")


class FakeSession:
    def __init__(self, name: str) -> None:
        self.name = name
        self.events: list[str] = []

    async def __aenter__(self) -> "FakeSession":
        self.events.append("session_enter")
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        self.events.append("session_exit")

    def begin(self) -> FakeTransaction:
        return FakeTransaction(self)


class FakeSessionFactory:
    def __init__(self) -> None:
        self.sessions: list[FakeSession] = []

    def __call__(self) -> FakeSession:
        session = FakeSession(name=f"session-{len(self.sessions) + 1}")
        self.sessions.append(session)
        return session


@pytest.mark.asyncio
async def test_process_one_returns_idle_when_nothing_is_claimed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = FakeSessionFactory()

    async def fake_claim(session: Any) -> None:
        assert session is factory.sessions[0]
        return None

    async def handler(
        session: Any,
        event: OutboxEvent,
        payload: UsageCompletedEvent,
    ) -> None:
        raise AssertionError("handler must not run while IDLE")

    monkeypatch.setattr(
        "bcos_worker.consumer.claim_next_event",
        fake_claim,
    )

    result = await process_one(
        factory,  # type: ignore[arg-type]
        handler,
    )

    assert result == ConsumerIterationResult.IDLE
    assert len(factory.sessions) == 1
    assert factory.sessions[0].events == [
        "session_enter",
        "transaction_begin",
        "commit",
        "session_exit",
    ]


@pytest.mark.asyncio
async def test_process_one_commits_claim_before_processing_and_marks_processed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = make_event()
    factory = FakeSessionFactory()
    calls: list[tuple[str, object]] = []

    async def fake_claim(session: Any) -> OutboxEvent:
        calls.append(("claim", session))
        return event

    async def fake_mark_processed(
        session: Any,
        received_event: OutboxEvent,
    ) -> bool:
        calls.append(("processed", session))
        assert received_event is event
        return True

    async def fake_retry(*args: object, **kwargs: object) -> bool:
        raise AssertionError("retry must not run on success")

    async def handler(
        session: Any,
        received_event: OutboxEvent,
        payload: UsageCompletedEvent,
    ) -> None:
        calls.append(("handler", session))
        assert received_event is event
        assert payload.usage_id == event.aggregate_id

    monkeypatch.setattr(
        "bcos_worker.consumer.claim_next_event",
        fake_claim,
    )
    monkeypatch.setattr(
        "bcos_worker.consumer.mark_event_processed",
        fake_mark_processed,
    )
    monkeypatch.setattr(
        "bcos_worker.consumer.mark_event_for_retry",
        fake_retry,
    )

    result = await process_one(
        factory,  # type: ignore[arg-type]
        handler,
    )

    assert result == ConsumerIterationResult.PROCESSED
    assert len(factory.sessions) == 2

    claim_session, processing_session = factory.sessions

    assert claim_session.events == [
        "session_enter",
        "transaction_begin",
        "commit",
        "session_exit",
    ]
    assert processing_session.events == [
        "session_enter",
        "transaction_begin",
        "commit",
        "session_exit",
    ]

    assert calls == [
        ("claim", claim_session),
        ("handler", processing_session),
        ("processed", processing_session),
    ]


@pytest.mark.asyncio
async def test_process_one_rolls_back_processing_then_schedules_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = make_event()
    factory = FakeSessionFactory()
    calls: list[tuple[str, object]] = []
    handler_error = RuntimeError("temporary processing failure")

    async def fake_claim(session: Any) -> OutboxEvent:
        calls.append(("claim", session))
        return event

    async def fake_mark_processed(*args: object, **kwargs: object) -> bool:
        raise AssertionError("PROCESSED must not be attempted after handler failure")

    async def fake_retry(
        session: Any,
        received_event: OutboxEvent,
        error: BaseException,
    ) -> bool:
        calls.append(("retry", session))
        assert received_event is event
        assert error is handler_error
        return True

    async def handler(
        session: Any,
        received_event: OutboxEvent,
        payload: UsageCompletedEvent,
    ) -> None:
        calls.append(("handler", session))
        raise handler_error

    monkeypatch.setattr(
        "bcos_worker.consumer.claim_next_event",
        fake_claim,
    )
    monkeypatch.setattr(
        "bcos_worker.consumer.mark_event_processed",
        fake_mark_processed,
    )
    monkeypatch.setattr(
        "bcos_worker.consumer.mark_event_for_retry",
        fake_retry,
    )

    result = await process_one(
        factory,  # type: ignore[arg-type]
        handler,
    )

    assert result == ConsumerIterationResult.RETRY_SCHEDULED
    assert len(factory.sessions) == 3

    claim_session, processing_session, retry_session = factory.sessions

    assert claim_session.events[-2:] == ["commit", "session_exit"]
    assert processing_session.events[-2:] == ["rollback", "session_exit"]
    assert retry_session.events[-2:] == ["commit", "session_exit"]

    assert calls == [
        ("claim", claim_session),
        ("handler", processing_session),
        ("retry", retry_session),
    ]


@pytest.mark.asyncio
async def test_process_one_retries_when_processed_transition_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = make_event()
    factory = FakeSessionFactory()
    retry_errors: list[BaseException] = []

    async def fake_claim(session: Any) -> OutboxEvent:
        return event

    async def fake_mark_processed(
        session: Any,
        received_event: OutboxEvent,
    ) -> bool:
        assert received_event is event
        return False

    async def fake_retry(
        session: Any,
        received_event: OutboxEvent,
        error: BaseException,
    ) -> bool:
        retry_errors.append(error)
        return True

    async def handler(
        session: Any,
        received_event: OutboxEvent,
        payload: UsageCompletedEvent,
    ) -> None:
        return None

    monkeypatch.setattr(
        "bcos_worker.consumer.claim_next_event",
        fake_claim,
    )
    monkeypatch.setattr(
        "bcos_worker.consumer.mark_event_processed",
        fake_mark_processed,
    )
    monkeypatch.setattr(
        "bcos_worker.consumer.mark_event_for_retry",
        fake_retry,
    )

    result = await process_one(
        factory,  # type: ignore[arg-type]
        handler,
    )

    assert result == ConsumerIterationResult.RETRY_SCHEDULED
    assert len(retry_errors) == 1
    assert isinstance(retry_errors[0], RuntimeError)
    assert factory.sessions[1].events[-2:] == [
        "rollback",
        "session_exit",
    ]
    assert factory.sessions[2].events[-2:] == [
        "commit",
        "session_exit",
    ]
