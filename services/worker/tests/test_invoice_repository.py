from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from bcos_worker.invoice_repository import (
    InvoiceMaterializationError,
    get_or_create_per_usage_invoice,
)

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
PROFESSIONAL_ID = UUID("00000000-0000-0000-0000-000000000002")
OTHER_PROFESSIONAL_ID = UUID("00000000-0000-0000-0000-000000000003")
USAGE_ID = UUID("00000000-0000-0000-0000-000000000004")
INVOICE_ID = UUID("00000000-0000-0000-0000-000000000005")


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


def _invoice_row(*, professional_id=PROFESSIONAL_ID):
    return {
        "id": INVOICE_ID,
        "tenant_id": TENANT_ID,
        "professional_id": professional_id,
        "source_usage_id": USAGE_ID,
    }


@pytest.mark.asyncio
async def test_returns_existing_per_usage_invoice() -> None:
    session = AsyncMock()
    session.execute.return_value = _Result(rows=[_invoice_row()])

    invoice = await get_or_create_per_usage_invoice(
        session,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        usage_id=USAGE_ID,
    )

    assert invoice.id == INVOICE_ID
    assert invoice.tenant_id == TENANT_ID
    assert invoice.professional_id == PROFESSIONAL_ID
    assert invoice.source_usage_id == USAGE_ID
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_creates_per_usage_invoice_when_missing() -> None:
    session = AsyncMock()
    session.execute.side_effect = [
        _Result(rows=[]),
        _Result(one=_invoice_row()),
    ]

    invoice = await get_or_create_per_usage_invoice(
        session,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        usage_id=USAGE_ID,
    )

    assert invoice.id == INVOICE_ID
    assert invoice.source_usage_id == USAGE_ID
    assert session.execute.await_count == 2

    insert_parameters = session.execute.await_args_list[1].args[1]

    assert insert_parameters == {
        "tenant_id": TENANT_ID,
        "professional_id": PROFESSIONAL_ID,
        "usage_id": USAGE_ID,
    }


@pytest.mark.asyncio
async def test_resolves_same_invoice_after_concurrent_insert() -> None:
    session = AsyncMock()
    session.execute.side_effect = [
        _Result(rows=[]),
        _Result(one=None),
        _Result(one=_invoice_row()),
    ]

    invoice = await get_or_create_per_usage_invoice(
        session,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        usage_id=USAGE_ID,
    )

    assert invoice.id == INVOICE_ID
    assert invoice.source_usage_id == USAGE_ID
    assert session.execute.await_count == 3


@pytest.mark.asyncio
async def test_fails_closed_when_existing_invoice_has_other_professional() -> None:
    session = AsyncMock()
    session.execute.return_value = _Result(
        rows=[_invoice_row(professional_id=OTHER_PROFESSIONAL_ID)]
    )

    with pytest.raises(
        InvoiceMaterializationError,
        match="another professional",
    ):
        await get_or_create_per_usage_invoice(
            session,
            tenant_id=TENANT_ID,
            professional_id=PROFESSIONAL_ID,
            usage_id=USAGE_ID,
        )

    assert session.execute.await_count == 1