from __future__ import annotations

from uuid import uuid4

import pytest

from bcos_api.billing.repository import list_invoices


class _Mappings:
    def all(self):
        return []


class _Result:
    def mappings(self):
        return _Mappings()


class RecordingSession:
    def __init__(self) -> None:
        self.statement = None
        self.parameters = None

    async def execute(self, statement, parameters):
        self.statement = statement
        self.parameters = parameters
        return _Result()


@pytest.mark.asyncio
async def test_list_invoices_types_nullable_professional_filter_for_postgresql() -> None:
    session = RecordingSession()

    await list_invoices(
        session,
        tenant_id=uuid4(),
        professional_id=None,
        status=None,
        limit=50,
        offset=0,
    )

    sql = str(session.statement)
    assert "CAST(:professional_id AS UUID) IS NULL" in sql
    assert "professional_id = CAST(:professional_id AS UUID)" in sql
    assert session.parameters["professional_id"] is None
