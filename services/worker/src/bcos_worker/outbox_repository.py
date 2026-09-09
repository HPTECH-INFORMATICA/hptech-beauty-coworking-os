"""Persistence operations for the BCOS transactional Outbox."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_worker.outbox import OutboxEvent, OutboxStatus


async def claim_next_event(
    session: AsyncSession,
) -> OutboxEvent | None:
    """Atomically claim the next eligible Outbox event."""

    result = await session.execute(
        text(
            """
            WITH next_event AS (
                SELECT id
                FROM outbox_events
                WHERE status = 'PENDING'
                  AND available_at <= now()
                ORDER BY available_at, created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE outbox_events AS oe
            SET
                status = 'PROCESSING',
                attempts = oe.attempts + 1,
                last_error = NULL
            FROM next_event AS ne
            WHERE oe.id = ne.id
            RETURNING
                oe.id,
                oe.tenant_id,
                oe.dedupe_key,
                oe.event_type,
                oe.aggregate_type,
                oe.aggregate_id,
                oe.payload,
                oe.status,
                oe.attempts,
                oe.available_at,
                oe.processed_at,
                oe.last_error,
                oe.created_at
            """
        )
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    payload: dict[str, Any] = dict(row["payload"])

    return OutboxEvent(
        id=row["id"],
        tenant_id=row["tenant_id"],
        dedupe_key=row["dedupe_key"],
        event_type=row["event_type"],
        aggregate_type=row["aggregate_type"],
        aggregate_id=row["aggregate_id"],
        payload=payload,
        status=OutboxStatus(row["status"]),
        attempts=row["attempts"],
        available_at=row["available_at"],
        processed_at=row["processed_at"],
        last_error=row["last_error"],
        created_at=row["created_at"],
    )


async def mark_event_processed(
    session: AsyncSession,
    event: OutboxEvent,
) -> bool:
    """Mark a claimed Outbox event as successfully processed."""

    result = await session.execute(
        text(
            """
            UPDATE outbox_events
            SET
                status = 'PROCESSED',
                processed_at = now(),
                last_error = NULL
            WHERE id = :event_id
              AND tenant_id = :tenant_id
              AND status = 'PROCESSING'
            RETURNING id
            """
        ),
        {
            "event_id": event.id,
            "tenant_id": event.tenant_id,
        },
    )

    return result.scalar_one_or_none() is not None
