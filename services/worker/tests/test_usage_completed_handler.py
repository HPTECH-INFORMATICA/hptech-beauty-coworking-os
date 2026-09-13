"""Unit tests for transactional USAGE_COMPLETED Billing dispatch."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

import bcos_worker.usage_completed_handler as usage_completed_handler
from bcos_worker.dispatcher import UsageCompletedEvent
from bcos_worker.invoice_repository import InvoiceMaterializationError
from bcos_worker.outbox import OutboxEvent, OutboxStatus


def _make_event_and_payload() -> tuple[OutboxEvent, UsageCompletedEvent]:
    checked_out_at = datetime(2026, 9, 13, 15, 0, tzinfo=UTC)
    usage_id = uuid4()
    tenant_id = uuid4()

    event = OutboxEvent(
        id=uuid4(),
        tenant_id=tenant_id,
        dedupe_key=f"usage-completed:{usage_id}",
        event_type="USAGE_COMPLETED",
        aggregate_type="USAGE",
        aggregate_id=usage_id,
        payload={
            "usage_id": str(usage_id),
            "checked_out_at": checked_out_at.isoformat(),
        },
        status=OutboxStatus.PROCESSING,
        attempts=1,
        available_at=checked_out_at,
        processing_started_at=checked_out_at,
        processed_at=None,
        last_error=None,
        created_at=checked_out_at,
    )
    payload = UsageCompletedEvent(
        usage_id=usage_id,
        checked_out_at=checked_out_at,
    )
    return event, payload


def _make_context(
    *,
    tenant_id: UUID,
    usage_id: UUID,
    checked_out_at: datetime,
    invoice_mode: str,
    usage_status: str = "COMPLETED",
) -> SimpleNamespace:
    return SimpleNamespace(
        tenant_id=tenant_id,
        usage_id=usage_id,
        usage_status=usage_status,
        checked_out_at=checked_out_at,
        professional_billing_contract=SimpleNamespace(invoice_mode=invoice_mode),
    )


@pytest.mark.asyncio
async def test_handle_usage_completed_dispatches_per_usage_only(monkeypatch: pytest.MonkeyPatch) -> None:
    event, payload = _make_event_and_payload()
    context = _make_context(
        tenant_id=event.tenant_id,
        usage_id=payload.usage_id,
        checked_out_at=payload.checked_out_at,
        invoice_mode="PER_USAGE",
    )
    hydrate = AsyncMock(return_value=context)
    per_usage = AsyncMock()
    accumulated = AsyncMock()
    monkeypatch.setattr(usage_completed_handler, "hydrate_usage_pricing_context", hydrate)
    monkeypatch.setattr(usage_completed_handler, "materialize_per_usage_invoice", per_usage)
    monkeypatch.setattr(
        usage_completed_handler,
        "materialize_accumulated_invoice",
        accumulated,
    )
    session = object()

    await usage_completed_handler.handle_usage_completed(session, event, payload)  # type: ignore[arg-type]

    hydrate.assert_awaited_once_with(
        session,
        tenant_id=event.tenant_id,
        usage_id=payload.usage_id,
    )
    per_usage.assert_awaited_once_with(session, context)
    accumulated.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_usage_completed_dispatches_accumulated_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event, payload = _make_event_and_payload()
    context = _make_context(
        tenant_id=event.tenant_id,
        usage_id=payload.usage_id,
        checked_out_at=payload.checked_out_at,
        invoice_mode="ACCUMULATED_OPEN_INVOICE",
    )
    hydrate = AsyncMock(return_value=context)
    per_usage = AsyncMock()
    accumulated = AsyncMock()
    monkeypatch.setattr(usage_completed_handler, "hydrate_usage_pricing_context", hydrate)
    monkeypatch.setattr(usage_completed_handler, "materialize_per_usage_invoice", per_usage)
    monkeypatch.setattr(
        usage_completed_handler,
        "materialize_accumulated_invoice",
        accumulated,
    )
    session = object()

    await usage_completed_handler.handle_usage_completed(session, event, payload)  # type: ignore[arg-type]

    accumulated.assert_awaited_once_with(session, context)
    per_usage.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("override", "expected_message"),
    [
        ({"tenant_id": uuid4()}, "hydrated context belongs to another tenant"),
        ({"usage_id": uuid4()}, "hydrated context belongs to another Usage"),
        ({"usage_status": "PENDING"}, "Billing requires a completed Usage"),
        (
            {"checked_out_at": datetime(2026, 9, 13, 16, 0, tzinfo=UTC)},
            "payload checked_out_at differs from authoritative Usage",
        ),
    ],
)
async def test_handle_usage_completed_fails_closed_on_context_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    override: dict[str, object],
    expected_message: str,
) -> None:
    event, payload = _make_event_and_payload()
    context = _make_context(
        tenant_id=event.tenant_id,
        usage_id=payload.usage_id,
        checked_out_at=payload.checked_out_at,
        invoice_mode="PER_USAGE",
    )
    for name, value in override.items():
        setattr(context, name, value)

    per_usage = AsyncMock()
    accumulated = AsyncMock()
    monkeypatch.setattr(
        usage_completed_handler,
        "hydrate_usage_pricing_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(usage_completed_handler, "materialize_per_usage_invoice", per_usage)
    monkeypatch.setattr(
        usage_completed_handler,
        "materialize_accumulated_invoice",
        accumulated,
    )

    with pytest.raises(InvoiceMaterializationError, match=expected_message):
        await usage_completed_handler.handle_usage_completed(object(), event, payload)  # type: ignore[arg-type]

    per_usage.assert_not_awaited()
    accumulated.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_usage_completed_rejects_unsupported_invoice_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event, payload = _make_event_and_payload()
    context = _make_context(
        tenant_id=event.tenant_id,
        usage_id=payload.usage_id,
        checked_out_at=payload.checked_out_at,
        invoice_mode="UNSUPPORTED",
    )
    per_usage = AsyncMock()
    accumulated = AsyncMock()
    monkeypatch.setattr(
        usage_completed_handler,
        "hydrate_usage_pricing_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(usage_completed_handler, "materialize_per_usage_invoice", per_usage)
    monkeypatch.setattr(
        usage_completed_handler,
        "materialize_accumulated_invoice",
        accumulated,
    )

    with pytest.raises(
        InvoiceMaterializationError,
        match="Unsupported invoice materialization mode: UNSUPPORTED",
    ):
        await usage_completed_handler.handle_usage_completed(object(), event, payload)  # type: ignore[arg-type]

    per_usage.assert_not_awaited()
    accumulated.assert_not_awaited()
