"""HTTP regression tests for the BCOS Professionals router."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from bcos_api.professionals.domain import (
    Professional,
    ProfessionalStatus,
)
from bcos_api.professionals.router import update_professional
from bcos_api.professionals.schemas import ProfessionalUpdate
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole


class FakeSession:
    """Minimal async session double for router transaction assertions."""

    def __init__(self) -> None:
        self.commit_called = False
        self.rollback_called = False

    async def commit(self) -> None:
        self.commit_called = True

    async def rollback(self) -> None:
        self.rollback_called = True


@pytest.mark.asyncio
async def test_patch_integrity_conflict_returns_409_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid4()
    professional_id = uuid4()

    context = TenantContext(
        tenant_id=tenant_id,
        membership_id=uuid4(),
        external_user_id="identity-owner",
        role=MembershipRole.OWNER,
    )
    current = Professional(
        id=professional_id,
        tenant_id=tenant_id,
        external_user_id="hptech-user-1",
        name="Cristiana Valente",
        email="contato@example.com",
        phone="41999999999",
        status=ProfessionalStatus.ACTIVE,
    )
    session = FakeSession()

    async def fake_get_tenant_professional(
        *args: object,
        **kwargs: object,
    ) -> Professional:
        return current

    async def fake_update_tenant_professional(
        *args: object,
        **kwargs: object,
    ) -> Professional:
        raise IntegrityError(
            "UPDATE professionals",
            {},
            Exception("unique violation"),
        )

    monkeypatch.setattr(
        "bcos_api.professionals.router.get_tenant_professional",
        fake_get_tenant_professional,
    )
    monkeypatch.setattr(
        "bcos_api.professionals.router.update_tenant_professional",
        fake_update_tenant_professional,
    )

    payload = ProfessionalUpdate(
        external_user_id="hptech-user-duplicate",
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_professional(
            professional_id=professional_id,
            payload=payload,
            session=session,  # type: ignore[arg-type]
            context=context,
        )

    assert exc_info.value.status_code == 409
    assert (
        exc_info.value.detail
        == "Professional conflicts with an existing record."
    )
    assert session.rollback_called is True
    assert session.commit_called is False
