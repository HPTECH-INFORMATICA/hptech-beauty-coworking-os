"""Unit tests for the approved BCOS worker runtime loop."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from bcos_worker.consumer import ConsumerIterationResult
from bcos_worker.runtime import (
    IDLE_SLEEP_SECONDS,
    RECOVERY_INTERVAL_SECONDS,
    run_recovery,
    run_worker,
)


@pytest.mark.asyncio
async def test_run_recovery_uses_its_own_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class Transaction:
        async def __aenter__(self) -> None:
            events.append("begin")

        async def __aexit__(
            self,
            exc_type: object,
            exc: object,
            traceback: object,
        ) -> None:
            events.append("commit" if exc_type is None else "rollback")

    class Session:
        async def __aenter__(self) -> "Session":
            events.append("session_enter")
            return self

        async def __aexit__(
            self,
            exc_type: object,
            exc: object,
            traceback: object,
        ) -> None:
            events.append("session_exit")

        def begin(self) -> Transaction:
            return Transaction()

    class Factory:
        def __call__(self) -> Session:
            return Session()

    async def fake_recovery(session: Any) -> int:
        events.append("recovery")
        return 2

    monkeypatch.setattr(
        "bcos_worker.runtime.recover_abandoned_events",
        fake_recovery,
    )

    recovered = await run_recovery(Factory())  # type: ignore[arg-type]

    assert recovered == 2
    assert events == [
        "session_enter",
        "begin",
        "recovery",
        "commit",
        "session_exit",
    ]


@pytest.mark.asyncio
async def test_worker_runs_startup_recovery_before_first_iteration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def fake_recovery(session_factory: Any) -> int:
        calls.append("recovery")
        return 0

    async def fake_process(
        session_factory: Any,
        handler: Any,
    ) -> ConsumerIterationResult:
        calls.append("process")
        raise asyncio.CancelledError

    monkeypatch.setattr("bcos_worker.runtime.run_recovery", fake_recovery)
    monkeypatch.setattr("bcos_worker.runtime.process_one", fake_process)

    async def handler(*args: Any) -> None:
        return None

    with pytest.raises(asyncio.CancelledError):
        await run_worker(
            object(),  # type: ignore[arg-type]
            handler,
            clock=lambda: 0.0,
        )

    assert calls == ["recovery", "process"]


@pytest.mark.asyncio
async def test_worker_sleeps_five_seconds_only_when_idle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = iter(
        [
            ConsumerIterationResult.PROCESSED,
            ConsumerIterationResult.RETRY_SCHEDULED,
            ConsumerIterationResult.IDLE,
        ]
    )
    sleeps: list[float] = []

    async def fake_recovery(session_factory: Any) -> int:
        return 0

    async def fake_process(
        session_factory: Any,
        handler: Any,
    ) -> ConsumerIterationResult:
        try:
            return next(results)
        except StopIteration:
            raise asyncio.CancelledError from None

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("bcos_worker.runtime.run_recovery", fake_recovery)
    monkeypatch.setattr("bcos_worker.runtime.process_one", fake_process)

    async def handler(*args: Any) -> None:
        return None

    with pytest.raises(asyncio.CancelledError):
        await run_worker(
            object(),  # type: ignore[arg-type]
            handler,
            sleep=fake_sleep,
            clock=lambda: 0.0,
        )

    assert sleeps == [IDLE_SLEEP_SECONDS]
    assert IDLE_SLEEP_SECONDS == 5.0


@pytest.mark.asyncio
async def test_worker_runs_periodic_recovery_after_sixty_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    clock_values = iter([0.0, 0.0, RECOVERY_INTERVAL_SECONDS, RECOVERY_INTERVAL_SECONDS])

    async def fake_recovery(session_factory: Any) -> int:
        calls.append("recovery")
        if calls.count("recovery") == 2:
            raise asyncio.CancelledError
        return 0

    async def fake_process(
        session_factory: Any,
        handler: Any,
    ) -> ConsumerIterationResult:
        calls.append("process")
        return ConsumerIterationResult.PROCESSED

    monkeypatch.setattr("bcos_worker.runtime.run_recovery", fake_recovery)
    monkeypatch.setattr("bcos_worker.runtime.process_one", fake_process)

    async def handler(*args: Any) -> None:
        return None

    with pytest.raises(asyncio.CancelledError):
        await run_worker(
            object(),  # type: ignore[arg-type]
            handler,
            clock=lambda: next(clock_values),
        )

    assert calls == ["recovery", "process", "recovery"]
