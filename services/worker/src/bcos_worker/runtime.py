"""Runtime loop for the approved BCOS Outbox consumer lifecycle."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from time import monotonic

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bcos_worker.consumer import (
    ConsumerIterationResult,
    TransactionalUsageCompletedHandler,
    process_one,
)
from bcos_worker.outbox_repository import recover_abandoned_events

IDLE_SLEEP_SECONDS = 5.0
RECOVERY_INTERVAL_SECONDS = 60.0

Sleep = Callable[[float], Awaitable[None]]
Clock = Callable[[], float]


async def run_recovery(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Run abandoned PROCESSING recovery in its own short transaction."""

    async with session_factory() as session:
        async with session.begin():
            return await recover_abandoned_events(session)


async def run_worker(
    session_factory: async_sessionmaker[AsyncSession],
    usage_completed_handler: TransactionalUsageCompletedHandler,
    *,
    sleep: Sleep = asyncio.sleep,
    clock: Clock = monotonic,
) -> None:
    """Run the sequential worker loop under the approved T6 contract."""

    await run_recovery(session_factory)
    last_recovery_at = clock()

    while True:
        now = clock()

        if now - last_recovery_at >= RECOVERY_INTERVAL_SECONDS:
            await run_recovery(session_factory)
            last_recovery_at = clock()

        result = await process_one(
            session_factory,
            usage_completed_handler,
        )

        if result is ConsumerIterationResult.IDLE:
            await sleep(IDLE_SLEEP_SECONDS)
