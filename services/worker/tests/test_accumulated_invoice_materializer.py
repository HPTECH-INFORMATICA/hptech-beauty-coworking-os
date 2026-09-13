from __future__ import annotations

from datetime import UTC, datetime, time
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from bcos_worker.accumulated_invoice_materializer import (
    materialize_accumulated_invoice,
)
from bcos_worker.invoice_repository import (
    AccumulatedInvoiceIdentity,
    InvoiceMaterializationError,
)
from bcos_worker.pricing_context import ReceptionHours, UsagePricingContext
from bcos_worker.pricing_rule import (
    OvertimeRule,
    PricingModality,
    PricingRuleDefinitionV1,
)
from bcos_worker.professional_billing_contract import ProfessionalBillingContract

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
USAGE_ID = UUID("00000000-0000-0000-0000-000000000002")
BOOKING_ID = UUID("00000000-0000-0000-0000-000000000003")
RESOURCE_ID = UUID("00000000-0000-0000-0000-000000000004")
PROFESSIONAL_ID = UUID("00000000-0000-0000-0000-000000000005")
UNIT_ID = UUID("00000000-0000-0000-0000-000000000006")
CONTRACT_ID = UUID("00000000-0000-0000-0000-000000000007")
INVOICE_ID = UUID("00000000-0000-0000-0000-000000000008")
BASE_ITEM_ID = UUID("00000000-0000-0000-0000-000000000009")
OVERTIME_ITEM_ID = UUID("00000000-0000-0000-0000-000000000010")


class _Mappings:
    def __init__(self, *, rows=None, one=None):
        self._rows = [] if rows is None else rows
        self._one = one

    def all(self):
        return self._rows

    def one(self):
        return self._one


class _MappingResult:
    def __init__(self, *, rows=None, one=None):
        self._mappings = _Mappings(rows=rows, one=one)

    def mappings(self):
        return self._mappings


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _context(
    *,
    invoice_mode: str = "ACCUMULATED_OPEN_INVOICE",
    lifecycle_mode: str | None = "WEEKLY",
    allocation_policy: str | None = "USAGE_COMPLETION",
) -> UsagePricingContext:
    zone = ZoneInfo("America/Sao_Paulo")
    booking_starts_at = datetime(2026, 9, 11, 19, 30, tzinfo=UTC)
    booking_ends_at = datetime(2026, 9, 11, 20, 30, tzinfo=UTC)
    checked_out_at = datetime(2026, 9, 11, 21, 20, tzinfo=UTC)

    pricing_rule = PricingRuleDefinitionV1(
        schema_version=1,
        modality=PricingModality.HOURLY,
        base_price_amount=Decimal("100.00"),
        overtime=OvertimeRule(
            hourly_price_amount=Decimal("60.00"),
            proportional_until_minutes=29,
            full_hour_from_minutes=30,
            forgiveness_allowed=True,
        ),
        conflict_penalty=None,
    )

    contract = ProfessionalBillingContract(
        id=CONTRACT_ID,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        invoice_mode=invoice_mode,
        valid_from=datetime(2026, 9, 1, tzinfo=UTC),
        valid_until=None,
        lifecycle_mode=lifecycle_mode,
        lifecycle_weekday=4 if lifecycle_mode == "WEEKLY" else None,
        lifecycle_biweekly_anchor=None,
        lifecycle_month_day=None,
        lifecycle_closing_time=(
            time(18, 0) if lifecycle_mode not in {None, "MANUAL"} else None
        ),
        cycle_allocation_policy=allocation_policy,
    )

    return UsagePricingContext(
        tenant_id=TENANT_ID,
        usage_id=USAGE_ID,
        booking_id=BOOKING_ID,
        resource_id=RESOURCE_ID,
        professional_id=PROFESSIONAL_ID,
        unit_id=UNIT_ID,
        usage_status="COMPLETED",
        checked_in_at=booking_starts_at,
        checked_out_at=checked_out_at,
        booking_starts_at=booking_starts_at,
        booking_ends_at=booking_ends_at,
        pricing_snapshot={},
        pricing_rule=pricing_rule,
        professional_billing_contract=contract,
        unit_timezone="America/Sao_Paulo",
        local_checked_out_at=checked_out_at.astimezone(zone),
        reception_hours=ReceptionHours(
            day_of_week=4,
            opens_at=time(8, 0),
            closes_at=time(18, 0),
            is_closed=False,
        ),
    )


def _invoice() -> AccumulatedInvoiceIdentity:
    return AccumulatedInvoiceIdentity(
        id=INVOICE_ID,
        tenant_id=TENANT_ID,
        professional_id=PROFESSIONAL_ID,
        professional_billing_contract_id=CONTRACT_ID,
        billing_cycle_start=datetime(2026, 9, 11, 21, 0, tzinfo=UTC),
        billing_cycle_end=datetime(2026, 9, 18, 21, 0, tzinfo=UTC),
        manual_closed_at=None,
        status="OPEN",
    )


def _base_item_row(*, invoice_id=INVOICE_ID):
    return {
        "id": BASE_ITEM_ID,
        "invoice_id": invoice_id,
        "tenant_id": TENANT_ID,
        "usage_id": USAGE_ID,
        "item_type": "BASE_LEASE",
        "description": "Base lease",
        "quantity": Decimal("1"),
        "unit_amount": Decimal("100.00"),
        "total_amount": Decimal("100.00"),
        "metadata": {},
        "billing_period_start": None,
        "billing_period_end": None,
    }


def _overtime_item_row():
    return {
        "id": OVERTIME_ITEM_ID,
        "invoice_id": INVOICE_ID,
        "tenant_id": TENANT_ID,
        "usage_id": USAGE_ID,
        "item_type": "OVERTIME",
        "description": "Overtime",
        "quantity": Decimal("50"),
        "unit_amount": Decimal("60.00"),
        "total_amount": Decimal("80.00"),
        "metadata": {
            "forgiveness_allowed": True,
            "reception_segments": [
                {
                    "segment": "BEFORE_RECEPTION_CLOSE",
                    "completed_minutes": 30,
                    "amount": "60.00",
                },
                {
                    "segment": "AFTER_RECEPTION_CLOSE",
                    "completed_minutes": 20,
                    "amount": "20.00",
                },
            ],
        },
        "billing_period_start": None,
        "billing_period_end": None,
    }


@pytest.mark.asyncio
async def test_materializes_usage_completion_into_accumulated_invoice(
    monkeypatch,
) -> None:
    context = _context()
    session = AsyncMock()

    async def _get_invoice(*args, **kwargs):
        return _invoice()

    monkeypatch.setattr(
        "bcos_worker.accumulated_invoice_materializer.get_or_create_accumulated_invoice",
        _get_invoice,
    )

    session.execute.side_effect = [
        object(),
        _MappingResult(rows=[_base_item_row()]),
        object(),
        _MappingResult(rows=[_overtime_item_row()]),
        _MappingResult(
            one={
                "subtotal_amount": Decimal("180.00"),
                "discount_amount": Decimal("0.00"),
            }
        ),
        _ScalarResult(INVOICE_ID),
    ]

    result = await materialize_accumulated_invoice(session, context)

    assert result.invoice.id == INVOICE_ID
    assert result.subtotal_amount == Decimal("180.00")
    assert result.discount_amount == Decimal("0.00")
    assert result.total_amount == Decimal("180.00")
    assert session.execute.await_count == 6

    base_params = session.execute.await_args_list[0].args[1]
    assert base_params["item_type"] == "BASE_LEASE"
    assert base_params["total_amount"] == Decimal("100.00")

    overtime_params = session.execute.await_args_list[2].args[1]
    assert overtime_params["item_type"] == "OVERTIME"
    assert overtime_params["quantity"] == Decimal("50")
    assert overtime_params["total_amount"] == Decimal("80.00")

    totals_params = session.execute.await_args_list[5].args[1]
    assert totals_params["subtotal_amount"] == Decimal("180.00")
    assert totals_params["discount_amount"] == Decimal("0.00")
    assert totals_params["total_amount"] == Decimal("180.00")


@pytest.mark.asyncio
async def test_retry_reuses_existing_accumulated_invoice_items(
    monkeypatch,
) -> None:
    context = _context()
    session = AsyncMock()

    async def _get_invoice(*args, **kwargs):
        return _invoice()

    monkeypatch.setattr(
        "bcos_worker.accumulated_invoice_materializer.get_or_create_accumulated_invoice",
        _get_invoice,
    )

    session.execute.side_effect = [
        object(),
        _MappingResult(rows=[_base_item_row()]),
        object(),
        _MappingResult(rows=[_overtime_item_row()]),
        _MappingResult(
            one={
                "subtotal_amount": Decimal("180.00"),
                "discount_amount": Decimal("0.00"),
            }
        ),
        _ScalarResult(INVOICE_ID),
    ]

    first = await materialize_accumulated_invoice(session, context)

    session.reset_mock()
    session.execute.side_effect = [
        object(),
        _MappingResult(rows=[_base_item_row()]),
        object(),
        _MappingResult(rows=[_overtime_item_row()]),
        _MappingResult(
            one={
                "subtotal_amount": Decimal("180.00"),
                "discount_amount": Decimal("0.00"),
            }
        ),
        _ScalarResult(INVOICE_ID),
    ]

    second = await materialize_accumulated_invoice(session, context)

    assert first.invoice.id == second.invoice.id == INVOICE_ID
    assert first.total_amount == second.total_amount == Decimal("180.00")
    assert session.execute.await_count == 6


@pytest.mark.asyncio
async def test_fails_closed_when_existing_item_belongs_to_another_invoice(
    monkeypatch,
) -> None:
    context = _context()
    session = AsyncMock()
    other_invoice_id = UUID("00000000-0000-0000-0000-000000000099")

    async def _get_invoice(*args, **kwargs):
        return _invoice()

    monkeypatch.setattr(
        "bcos_worker.accumulated_invoice_materializer.get_or_create_accumulated_invoice",
        _get_invoice,
    )

    session.execute.side_effect = [
        object(),
        _MappingResult(rows=[_base_item_row(invoice_id=other_invoice_id)]),
    ]

    with pytest.raises(
        InvoiceMaterializationError,
        match="another Invoice",
    ):
        await materialize_accumulated_invoice(session, context)


@pytest.mark.asyncio
async def test_fixed_cutoff_split_fails_closed_before_database_writes() -> None:
    context = _context(allocation_policy="FIXED_CUTOFF_SPLIT")
    session = AsyncMock()

    with pytest.raises(
        InvoiceMaterializationError,
        match="deterministic temporal financial segmentation",
    ):
        await materialize_accumulated_invoice(session, context)

    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_rejects_non_accumulated_contract() -> None:
    context = _context(
        invoice_mode="PER_USAGE",
        lifecycle_mode=None,
        allocation_policy=None,
    )
    session = AsyncMock()

    with pytest.raises(
        InvoiceMaterializationError,
        match="non-accumulated",
    ):
        await materialize_accumulated_invoice(session, context)

    assert session.execute.await_count == 0
