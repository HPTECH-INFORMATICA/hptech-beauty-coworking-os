"""Persistence operations for the BCOS transactional Outbox."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_worker.outbox import OutboxEvent, OutboxStatus

_MAX_LAST_ERROR_LENGTH = 500
_MAX_RETRY_DELAY_SECONDS = 900
_BASE_RETRY_DELAY_SECONDS = 30

_SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b("
    r"database_url|authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"token|secret|password|passwd|credential"
    r")\b\s*[:=]\s*([^\s,;]+)"
)

_POSTGRES_URL_PATTERN = re.compile(r"(?i)\bpostgres(?:ql)?(?:\+\w+)?://[^\s]+")

_BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bbearer\s+[^\s,;]+")

_AUTHORIZATION_PATTERN = re.compile(r"(?i)\bauthorization\b\s*[:=]\s*[^\s,;]+(?:\s+[^\s,;]+)?")


def retry_delay_seconds(attempts: int) -> int:
    """Return the approved bounded exponential retry delay."""
    if attempts < 1:
        raise ValueError("attempts must be greater than or equal to 1")

    return min(
        _BASE_RETRY_DELAY_SECONDS * (2 ** (attempts - 1)),
        _MAX_RETRY_DELAY_SECONDS,
    )


def sanitize_outbox_error(error: BaseException) -> str:
    """Return the approved safe diagnostic representation for last_error."""
    exception_class = type(error).__name__
    message = str(error)

    message = message.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    message = " ".join(message.split())

    message = _POSTGRES_URL_PATTERN.sub("[REDACTED]", message)
    message = _BEARER_TOKEN_PATTERN.sub("Bearer [REDACTED]", message)
    message = _AUTHORIZATION_PATTERN.sub("Authorization=[REDACTED]", message)
    message = _SENSITIVE_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        message,
    )

    sanitized = f"{exception_class}: {message}" if message else exception_class

    return sanitized[:_MAX_LAST_ERROR_LENGTH]


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
                processing_started_at = now(),
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
                oe.processing_started_at,
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
        processing_started_at=row["processing_started_at"],
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
                processing_started_at = NULL,
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


async def mark_event_for_retry(
    session: AsyncSession,
    event: OutboxEvent,
    error: BaseException,
) -> bool:
    """Return a recoverable processing failure to PENDING with approved retry delay."""

    delay_seconds = retry_delay_seconds(event.attempts)
    last_error = sanitize_outbox_error(error)

    result = await session.execute(
        text(
            """
            UPDATE outbox_events
            SET
                status = 'PENDING',
                processing_started_at = NULL,
                last_error = :last_error,
                available_at = now() + (:delay_seconds * INTERVAL '1 second')
            WHERE id = :event_id
              AND tenant_id = :tenant_id
              AND status = 'PROCESSING'
            RETURNING id
            """
        ),
        {
            "event_id": event.id,
            "tenant_id": event.tenant_id,
            "last_error": last_error,
            "delay_seconds": delay_seconds,
        },
    )

    return result.scalar_one_or_none() is not None
