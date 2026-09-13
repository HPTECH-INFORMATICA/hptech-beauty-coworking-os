from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from bcos_worker.billing_cycle import BillingCycle
from bcos_worker.invoice_repository import (
    InvoiceMaterializationError,
    get_or_create_accumulated_invoice,
)

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
PROFESSIONAL_ID = UUID("00000000-0000-0000-0000-000000000002")
OTHER_PROFESSIONAL_ID = UUID("00000000-0000-0000-0000-000000000003")
CONTRACT_ID = UUID("00000000-0000-0000-0000-000000000004")
INVOICE_ID = UUID("00000000-0000-0000-0000-000000000005")

CYCLE = BillingCycle(
    start=datetime(2026, 9, 11, 21, 0, tzinfo=UTC),
    end=datetime(2026, 9, 18, 21, 0, tzinfo=UTC),
)


class _Mappings:
    def __init__(self, *, rows=None, one=None):
        self._rows = [] if rows is None else rows
        self._one = one

    def all(self):
        return self._rows

    def one_or_none(self):
        return self._one


class _Result:
    def __init__(self, *, rows=None, one=None):
        self._mappings = _Mappings(rows=rows, one=one)

    def mappings(self):
        return self._mappings


def _row(
    *,
    professional_id=PROFESSIONAL_ID,
    cycle=CYCLE,
    status="OPEN",
    manual_closed_at=None,
):
    return {
        "id": INVOICE_ID,
        "tenant_id": TENANT_ID,
        "professional_id": professional_id,
        "source_usage_id": None,
        "professional_billing_contract_id": CONTRACT_ID,
        "billing_cycle_start": None if cycle is None else cycle.start,
        "billing_cycle_end": None if cycle is None else cycle.end,
        "manual_closed_at": manual_closed_at,
        "status": status,
    }


@pytest.mark.asyncio
async def test_returns_existing_automatic_accumulated_invoice() -> None:
    session = AsyncMock()
    session.execute.return_value = _Result(rows=[_row()])

    invoice = await get_or_create_accumulated_invoice(
        session,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        professional_billing_contract_id=CONTRACT_ID,
        cycle=CYCLE,
    )

    assert invoice.id == INVOICE_ID
    assert invoice.billing_cycle_start == CYCLE.start
    assert invoice.billing_cycle_end == CYCLE.end
    assert invoice.status == "OPEN"
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_creates_automatic_accumulated_invoice_when_missing() -> None:
    session = AsyncMock()
    session.execute.side_effect = [
        _Result(rows=[]),
        _Result(one=_row()),
    ]

    invoice = await get_or_create_accumulated_invoice(
        session,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        professional_billing_contract_id=CONTRACT_ID,
        cycle=CYCLE,
    )

    assert invoice.id == INVOICE_ID
    assert session.execute.await_count == 2

    params = session.execute.await_args_list[1].args[1]
    assert params["cycle_start"] == CYCLE.start
    assert params["cycle_end"] == CYCLE.end


@pytest.mark.asyncio
async def test_resolves_automatic_invoice_after_create_race() -> None:
    session = AsyncMock()
    session.execute.side_effect = [
        _Result(rows=[]),
        _Result(one=None),
        _Result(rows=[_row()]),
    ]

    invoice = await get_or_create_accumulated_invoice(
        session,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        professional_billing_contract_id=CONTRACT_ID,
        cycle=CYCLE,
    )

    assert invoice.id == INVOICE_ID
    assert session.execute.await_count == 3


@pytest.mark.asyncio
async def test_reuses_existing_manual_accumulated_invoice() -> None:
    session = AsyncMock()
    session.execute.return_value = _Result(rows=[_row(cycle=None)])

    invoice = await get_or_create_accumulated_invoice(
        session,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        professional_billing_contract_id=CONTRACT_ID,
        cycle=None,
    )

    assert invoice.id == INVOICE_ID
    assert invoice.billing_cycle_start is None
    assert invoice.billing_cycle_end is None


@pytest.mark.asyncio
async def test_creates_manual_invoice_when_no_eligible_invoice_exists() -> None:
    session = AsyncMock()
    session.execute.side_effect = [
        _Result(rows=[]),
        _Result(one=_row(cycle=None)),
    ]

    invoice = await get_or_create_accumulated_invoice(
        session,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        professional_billing_contract_id=CONTRACT_ID,
        cycle=None,
    )

    assert invoice.id == INVOICE_ID
    params = session.execute.await_args_list[1].args[1]
    assert params == {
        "tenant_id": TENANT_ID,
        "professional_id": PROFESSIONAL_ID,
        "contract_id": CONTRACT_ID,
    }


@pytest.mark.asyncio
async def test_fails_closed_for_multiple_manual_invoices() -> None:
    session = AsyncMock()
    session.execute.return_value = _Result(
        rows=[_row(cycle=None), _row(cycle=None)]
    )

    with pytest.raises(
        InvoiceMaterializationError,
        match="multiple accumulated Invoices",
    ):
        await get_or_create_accumulated_invoice(
            session,
            tenant_id=TENANT_ID,
            professional_id=PROFESSIONAL_ID,
            professional_billing_contract_id=CONTRACT_ID,
            cycle=None,
        )


@pytest.mark.asyncio
async def test_fails_closed_for_other_professional() -> None:
    session = AsyncMock()
    session.execute.return_value = _Result(
        rows=[_row(professional_id=OTHER_PROFESSIONAL_ID)]
    )

    with pytest.raises(
        InvoiceMaterializationError,
        match="another professional",
    ):
        await get_or_create_accumulated_invoice(
            session,
            tenant_id=TENANT_ID,
            professional_id=PROFESSIONAL_ID,
            professional_billing_contract_id=CONTRACT_ID,
            cycle=CYCLE,
        )


@pytest.mark.asyncio
async def test_fails_closed_for_non_open_invoice() -> None:
    session = AsyncMock()
    session.execute.return_value = _Result(rows=[_row(status="PAID")])

    with pytest.raises(
        InvoiceMaterializationError,
        match="not OPEN",
    ):
        await get_or_create_accumulated_invoice(
            session,
            tenant_id=TENANT_ID,
            professional_id=PROFESSIONAL_ID,
            professional_billing_contract_id=CONTRACT_ID,
            cycle=CYCLE,
        )
