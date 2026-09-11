"""Tests for historical professional Billing contract resolution."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from bcos_worker.professional_billing_contract import (
    ProfessionalBillingContractError,
    resolve_professional_billing_contract,
)


def _mapping_result(rows: list[dict[str, object]]) -> SimpleNamespace:
    mappings = SimpleNamespace(all=lambda: rows)
    return SimpleNamespace(mappings=lambda: mappings)


@pytest.mark.asyncio
async def test_resolves_contract_at_booking_start() -> None:
    tenant_id = uuid4()
    professional_id = uuid4()
    contract_id = uuid4()
    starts_at = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    valid_from = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)

    session = AsyncMock()
    session.execute.return_value = _mapping_result(
        [
            {
                "id": contract_id,
                "tenant_id": tenant_id,
                "professional_id": professional_id,
                "invoice_mode": "PER_USAGE",
                "valid_from": valid_from,
                "valid_until": None,
                "lifecycle_mode": None,
                "lifecycle_weekday": None,
                "lifecycle_biweekly_anchor": None,
                "lifecycle_month_day": None,
                "lifecycle_closing_time": None,
                "cycle_allocation_policy": None,
            }
        ]
    )

    contract = await resolve_professional_billing_contract(
        session,
        tenant_id=tenant_id,
        professional_id=professional_id,
        booking_starts_at=starts_at,
    )

    assert contract.id == contract_id
    assert contract.tenant_id == tenant_id
    assert contract.professional_id == professional_id
    assert contract.invoice_mode == "PER_USAGE"
    assert contract.valid_from == valid_from
    assert contract.valid_until is None

    params = session.execute.await_args.args[1]
    assert params == {
        "tenant_id": tenant_id,
        "professional_id": professional_id,
        "booking_starts_at": starts_at,
    }


@pytest.mark.asyncio
async def test_accepts_accumulated_open_invoice_mode() -> None:
    tenant_id = uuid4()
    professional_id = uuid4()
    starts_at = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)

    session = AsyncMock()
    session.execute.return_value = _mapping_result(
        [
            {
                "id": uuid4(),
                "tenant_id": tenant_id,
                "professional_id": professional_id,
                "invoice_mode": "ACCUMULATED_OPEN_INVOICE",
                "valid_from": datetime(
                    2026, 9, 1, 0, 0, tzinfo=UTC
                ),
                "valid_until": None,
                "lifecycle_mode": "MANUAL",
                "lifecycle_weekday": None,
                "lifecycle_biweekly_anchor": None,
                "lifecycle_month_day": None,
                "lifecycle_closing_time": None,
                "cycle_allocation_policy": "USAGE_COMPLETION",
            }
        ]
    )

    contract = await resolve_professional_billing_contract(
        session,
        tenant_id=tenant_id,
        professional_id=professional_id,
        booking_starts_at=starts_at,
    )

    assert contract.invoice_mode == "ACCUMULATED_OPEN_INVOICE"


@pytest.mark.asyncio
async def test_fails_closed_when_contract_is_missing() -> None:
    session = AsyncMock()
    session.execute.return_value = _mapping_result([])

    with pytest.raises(
        ProfessionalBillingContractError,
        match="not found",
    ):
        await resolve_professional_billing_contract(
            session,
            tenant_id=uuid4(),
            professional_id=uuid4(),
            booking_starts_at=datetime(
                2026, 9, 10, 12, 0, tzinfo=UTC
            ),
        )


@pytest.mark.asyncio
async def test_fails_closed_when_contract_is_ambiguous() -> None:
    tenant_id = uuid4()
    professional_id = uuid4()
    starts_at = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)

    def row() -> dict[str, object]:
        return {
            "id": uuid4(),
            "tenant_id": tenant_id,
            "professional_id": professional_id,
            "invoice_mode": "PER_USAGE",
            "valid_from": datetime(
                2026, 9, 1, 0, 0, tzinfo=UTC
            ),
            "valid_until": None,
            "lifecycle_mode": None,
            "lifecycle_weekday": None,
            "lifecycle_biweekly_anchor": None,
            "lifecycle_month_day": None,
            "lifecycle_closing_time": None,
            "cycle_allocation_policy": None,
        }

    session = AsyncMock()
    session.execute.return_value = _mapping_result([row(), row()])

    with pytest.raises(
        ProfessionalBillingContractError,
        match="ambiguous",
    ):
        await resolve_professional_billing_contract(
            session,
            tenant_id=tenant_id,
            professional_id=professional_id,
            booking_starts_at=starts_at,
        )


@pytest.mark.asyncio
async def test_rejects_naive_booking_start_before_query() -> None:
    session = AsyncMock()

    with pytest.raises(
        ProfessionalBillingContractError,
        match="timezone-aware",
    ):
        await resolve_professional_billing_contract(
            session,
            tenant_id=uuid4(),
            professional_id=uuid4(),
            booking_starts_at=datetime(2026, 9, 10, 12, 0),
        )

    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_unknown_invoice_mode() -> None:
    tenant_id = uuid4()
    professional_id = uuid4()

    session = AsyncMock()
    session.execute.return_value = _mapping_result(
        [
            {
                "id": uuid4(),
                "tenant_id": tenant_id,
                "professional_id": professional_id,
                "invoice_mode": "UNKNOWN",
                "valid_from": datetime(
                    2026, 9, 1, 0, 0, tzinfo=UTC
                ),
                "valid_until": None,
                "lifecycle_mode": None,
                "lifecycle_weekday": None,
                "lifecycle_biweekly_anchor": None,
                "lifecycle_month_day": None,
                "lifecycle_closing_time": None,
                "cycle_allocation_policy": None,
            }
        ]
    )

    with pytest.raises(
        ProfessionalBillingContractError,
        match="unsupported",
    ):
        await resolve_professional_billing_contract(
            session,
            tenant_id=tenant_id,
            professional_id=professional_id,
            booking_starts_at=datetime(
                2026, 9, 10, 12, 0, tzinfo=UTC
            ),
        )
