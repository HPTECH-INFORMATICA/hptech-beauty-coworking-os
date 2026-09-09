"""Transactional execution lifecycle for one BCOS Outbox event."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bcos_worker.dispatcher import (
    UsageCompletedEvent,
    dispatch_event,
)
from bcos_worker.outbox import OutboxEvent
from bcos_worker.outbox_repository import (
    claim_next_event,
    mark_event_for_retry,
    mark_event_processed,
)


class ConsumerIterationResult(StrEnum):
    """Outcome of one Outbox consumer iteration."""

    IDLE = "IDLE"
    PROCESSED = "PROCESSED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"


TransactionalUsageCompletedHandler = Callable[
    [AsyncSession, OutboxEvent, UsageCompletedEvent],
    Awaitable[None],
]


async def process_one(
    session_factory: async_sessionmaker[AsyncSession],
    usage_completed_handler: TransactionalUsageCompletedHandler,
) -> ConsumerIterationResult:
    """Process at most one eligible Outbox event under the approved T5 lifecycle."""

    async with session_factory() as claim_session:
        async with claim_session.begin():
            event = await claim_next_event(claim_session)

    if event is None:
        return ConsumerIterationResult.IDLE

    try:
        async with session_factory() as processing_session:
            async with processing_session.begin():

                async def transactional_handler(
                    received_event: OutboxEvent,
                    usage_completed: UsageCompletedEvent,
                ) -> None:
                    await usage_completed_handler(
                        processing_session,
                        received_event,
                        usage_completed,
                    )

                await dispatch_event(
                    event,
                    transactional_handler,
                )

                marked_processed = await mark_event_processed(
                    processing_session,
                    event,
                )

                if not marked_processed:
                    raise RuntimeError(
                        "Outbox event could not transition from PROCESSING to PROCESSED."
                    )

    except Exception as error:
        async with session_factory() as retry_session:
            async with retry_session.begin():
                retry_scheduled = await mark_event_for_retry(
                    retry_session,
                    event,
                    error,
                )

                if not retry_scheduled:
                    raise RuntimeError(
                        "Outbox event could not transition from PROCESSING to PENDING for retry."
                    ) from error

        return ConsumerIterationResult.RETRY_SCHEDULED

    return ConsumerIterationResult.PROCESSED
