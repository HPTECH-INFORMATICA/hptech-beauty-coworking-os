"""Tests for BCOS professional own-scope authorization."""

from __future__ import annotations

from uuid import uuid4

import pytest

from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.professional_scope import (
    ProfessionalScopeDenied,
    resolve_professional_scope,
)
from bcos_api.tenancy.rbac import PermissionDenied


class FakeMappings:
    def __init__(self, row: dict[str, object] | None) -> None:
        self._row = row

    def one_or_none(self) -> dict[str, object] | None:
        return self._row


class FakeResult:
    def __init__(self, row: dict[str, object] | None) -> None:
        self._row = row

    def mappings(self) -> FakeMappings:
        return FakeMappings(self._row)


class FakeSession:
    def __init__(self, row: dict[str, object] | None) -> None:
        self._row = row
        self.params: dict[str, object] | None = None

    async def execute(
        self,
        statement: object,
        params: dict[str, object],
    ) -> FakeResult:
        del statement
        self.params = params
        return FakeResult(self._row)


def make_context(
    *,
    role: MembershipRole = MembershipRole.PROFESSIONAL,
    tenant_id=None,
    external_user_id: str = "identity-professional",
) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id or uuid4(),
        membership_id=uuid4(),
        external_user_id=external_user_id,
        role=role,
    )


@pytest.mark.asyncio
async def test_professional_scope_is_derived_from_identity() -> None:
    tenant_id = uuid4()
    professional_id = uuid4()
    external_user_id = "identity-professional"

    context = make_context(
        tenant_id=tenant_id,
        external_user_id=external_user_id,
    )

    session = FakeSession(
        {
            "id": professional_id,
            "tenant_id": tenant_id,
            "external_user_id": external_user_id,
        }
    )

    scope = await resolve_professional_scope(
        session,  # type: ignore[arg-type]
        context=context,
    )

    assert scope.professional_id == professional_id
    assert scope.tenant_id == tenant_id
    assert scope.external_user_id == external_user_id
    assert session.params == {
        "tenant_id": tenant_id,
        "external_user_id": external_user_id,
    }


@pytest.mark.asyncio
async def test_missing_or_inactive_professional_is_denied() -> None:
    context = make_context()
    session = FakeSession(None)

    with pytest.raises(ProfessionalScopeDenied):
        await resolve_professional_scope(
            session,  # type: ignore[arg-type]
            context=context,
        )


@pytest.mark.asyncio
async def test_non_professional_role_is_denied_before_database_query() -> None:
    context = make_context(
        role=MembershipRole.RECEPTION,
    )
    session = FakeSession(None)

    with pytest.raises(PermissionDenied):
        await resolve_professional_scope(
            session,  # type: ignore[arg-type]
            context=context,
        )

    assert session.params is None
