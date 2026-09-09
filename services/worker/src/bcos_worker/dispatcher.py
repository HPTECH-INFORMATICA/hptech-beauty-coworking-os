"""Dispatch contract for BCOS Outbox events."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from bcos_worker.outbox import OutboxEvent


class UnsupportedOutboxEventError(RuntimeError):
    """Raised when the worker receives an unsupported Outbox event type."""


class InvalidOutboxPayloadError(RuntimeError):
    """Raised when a supported Outbox event has an invalid payload."""


@dataclass(frozen=True)
class UsageCompletedEvent:
    """Validated USAGE_COMPLETED event payload."""

    usage_id: UUID
    checked_out_at: datetime


UsageCompletedHandler = Callable[
    [OutboxEvent, UsageCompletedEvent],
    Awaitable[None],
]


def parse_usage_completed(
    event: OutboxEvent,
) -> UsageCompletedEvent:
    """Validate and parse the frozen USAGE_COMPLETED payload."""

    if event.event_type != "USAGE_COMPLETED":
        raise UnsupportedOutboxEventError(
            f"Unsupported Outbox event type: {event.event_type}"
        )

    usage_id_raw = event.payload.get("usage_id")
    checked_out_at_raw = event.payload.get("checked_out_at")

    if not isinstance(usage_id_raw, str):
        raise InvalidOutboxPayloadError(
            "USAGE_COMPLETED payload requires string usage_id."
        )

    if not isinstance(checked_out_at_raw, str):
        raise InvalidOutboxPayloadError(
            "USAGE_COMPLETED payload requires string checked_out_at."
        )

    try:
        usage_id = UUID(usage_id_raw)
    except ValueError as exc:
        raise InvalidOutboxPayloadError(
            "USAGE_COMPLETED payload contains invalid usage_id."
        ) from exc

    try:
        checked_out_at = datetime.fromisoformat(
            checked_out_at_raw.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise InvalidOutboxPayloadError(
            "USAGE_COMPLETED payload contains invalid checked_out_at."
        ) from exc

    if checked_out_at.tzinfo is None:
        raise InvalidOutboxPayloadError(
            "USAGE_COMPLETED checked_out_at must include timezone information."
        )

    return UsageCompletedEvent(
        usage_id=usage_id,
        checked_out_at=checked_out_at,
    )


async def dispatch_event(
    event: OutboxEvent,
    usage_completed_handler: UsageCompletedHandler,
) -> None:
    """Dispatch one supported Outbox event to its handler."""

    usage_completed = parse_usage_completed(event)

    await usage_completed_handler(
        event,
        usage_completed,
    )
