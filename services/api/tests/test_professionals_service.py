"""Permanent M2 tests for the BCOS Professional application service."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from bcos_api.professionals.domain import (
    InvalidProfessional,
    Professional,
    ProfessionalStatus,
)
from bcos_api.professionals.service import (
    ProfessionalNotFound,
    create_tenant_professional,
    get_tenant_professional,
    list_tenant_professionals,
    update_tenant_professional,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.rbac import PermissionDenied


def owner_context(*, tenant_id: UUID | None = None) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id or uuid4(),
        membership_id=uuid4(),
        external_user_id="identity-owner",
        role=MembershipRole.OWNER,
    )


def professional_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        membership_id=uuid4(),
        external_user_id="identity-professional",
        role=MembershipRole.PROFESSIONAL,
    )


def professional_for(
    *,
    tenant_id: UUID,
    professional_id: UUID | None = None,
    external_user_id: str | None = None,
    name: str = "Cristiana Valente",
    email: str | None = "contato@example.com",
    phone: str | None = "41999999999",
    status: ProfessionalStatus = ProfessionalStatus.ACTIVE,
) -> Professional:
    return Professional(
        id=professional_id or uuid4(),
        tenant_id=tenant_id,
        external_user_id=external_user_id,
        name=name,
        email=email,
        phone=phone,
        status=status,
    )


@pytest.mark.asyncio
async def test_list_professionals_uses_only_authorized_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    expected = [professional_for(tenant_id=context.tenant_id)]

    async def fake_list_professionals(
        session: object,
        *,
        tenant_id: UUID,
    ) -> list[Professional]:
        del session
        assert tenant_id == context.tenant_id
        return expected

    monkeypatch.setattr(
        "bcos_api.professionals.service.list_professionals",
        fake_list_professionals,
    )

    result = await list_tenant_professionals(
        object(),  # type: ignore[arg-type]
        context=context,
    )

    assert result == expected


@pytest.mark.asyncio
async def test_get_professional_cannot_fall_back_to_another_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    professional_id = uuid4()
    expected_professional_id = professional_id

    async def fake_get_professional(
        session: object,
        *,
        tenant_id: UUID,
        professional_id: UUID,
    ) -> Professional | None:
        del session
        assert tenant_id == context.tenant_id
        assert professional_id == expected_professional_id
        return None

    monkeypatch.setattr(
        "bcos_api.professionals.service.get_professional",
        fake_get_professional,
    )

    with pytest.raises(ProfessionalNotFound):
        await get_tenant_professional(
            object(),  # type: ignore[arg-type]
            context=context,
            professional_id=professional_id,
        )


@pytest.mark.asyncio
async def test_create_professional_uses_context_tenant_and_normalizes_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    created_id = uuid4()

    async def fake_create_professional(
        session: object,
        *,
        tenant_id: UUID,
        external_user_id: str | None,
        name: str,
        email: str | None,
        phone: str | None,
    ) -> Professional:
        del session
        assert tenant_id == context.tenant_id
        assert external_user_id == "hptech-user-1"
        assert name == "Cristiana Valente"
        assert email == "contato@example.com"
        assert phone == "41999999999"

        return professional_for(
            tenant_id=tenant_id,
            professional_id=created_id,
            external_user_id=external_user_id,
            name=name,
            email=email,
            phone=phone,
        )

    monkeypatch.setattr(
        "bcos_api.professionals.service.create_professional",
        fake_create_professional,
    )

    result = await create_tenant_professional(
        object(),  # type: ignore[arg-type]
        context=context,
        external_user_id="  hptech-user-1  ",
        name="  Cristiana Valente  ",
        email="  contato@example.com  ",
        phone="  41999999999  ",
    )

    assert result.id == created_id
    assert result.tenant_id == context.tenant_id
    assert result.external_user_id == "hptech-user-1"
    assert result.name == "Cristiana Valente"
    assert result.email == "contato@example.com"
    assert result.phone == "41999999999"


@pytest.mark.asyncio
async def test_create_professional_preserves_late_binding_nulls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()

    async def fake_create_professional(
        session: object,
        *,
        tenant_id: UUID,
        external_user_id: str | None,
        name: str,
        email: str | None,
        phone: str | None,
    ) -> Professional:
        del session
        assert tenant_id == context.tenant_id
        assert external_user_id is None
        assert email is None
        assert phone is None

        return professional_for(
            tenant_id=tenant_id,
            external_user_id=None,
            name=name,
            email=None,
            phone=None,
        )

    monkeypatch.setattr(
        "bcos_api.professionals.service.create_professional",
        fake_create_professional,
    )

    result = await create_tenant_professional(
        object(),  # type: ignore[arg-type]
        context=context,
        external_user_id="   ",
        name="Profissional sem convite",
        email="   ",
        phone=None,
    )

    assert result.external_user_id is None
    assert result.email is None
    assert result.phone is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", ""),
        ("name", "   "),
        ("name", "X" * 161),
        ("external_user_id", "X" * 256),
        ("email", "X" * 256),
        ("phone", "X" * 41),
    ],
)
async def test_create_rejects_invalid_fields_before_repository(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    context = owner_context()
    repository_called = False

    async def fake_create(*args: object, **kwargs: object) -> Professional:
        nonlocal repository_called
        repository_called = True
        raise AssertionError("Repository must not be called.")

    monkeypatch.setattr(
        "bcos_api.professionals.service.create_professional",
        fake_create,
    )

    values: dict[str, str | None] = {
        "external_user_id": None,
        "name": "Cristiana Valente",
        "email": None,
        "phone": None,
    }
    values[field] = value

    with pytest.raises(InvalidProfessional):
        await create_tenant_professional(
            object(),  # type: ignore[arg-type]
            context=context,
            external_user_id=values["external_user_id"],
            name=values["name"] or "",
            email=values["email"],
            phone=values["phone"],
        )

    assert repository_called is False


@pytest.mark.asyncio
async def test_update_professional_is_tenant_scoped_and_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    professional_id = uuid4()
    expected_professional_id = professional_id

    async def fake_update_professional(
        session: object,
        *,
        tenant_id: UUID,
        professional_id: UUID,
        external_user_id: str | None,
        name: str,
        email: str | None,
        phone: str | None,
        status: ProfessionalStatus,
    ) -> Professional:
        del session
        assert tenant_id == context.tenant_id
        assert professional_id == expected_professional_id
        assert external_user_id is None
        assert name == "Cristiana Valente"
        assert email == "novo@example.com"
        assert phone is None
        assert status is ProfessionalStatus.INACTIVE

        return professional_for(
            tenant_id=tenant_id,
            professional_id=professional_id,
            external_user_id=external_user_id,
            name=name,
            email=email,
            phone=phone,
            status=status,
        )

    monkeypatch.setattr(
        "bcos_api.professionals.service.update_professional",
        fake_update_professional,
    )

    result = await update_tenant_professional(
        object(),  # type: ignore[arg-type]
        context=context,
        professional_id=professional_id,
        external_user_id="   ",
        name="  Cristiana Valente  ",
        email="  novo@example.com  ",
        phone="   ",
        status=ProfessionalStatus.INACTIVE,
    )

    assert result.id == professional_id
    assert result.tenant_id == context.tenant_id
    assert result.external_user_id is None
    assert result.email == "novo@example.com"
    assert result.phone is None
    assert result.status is ProfessionalStatus.INACTIVE


@pytest.mark.asyncio
async def test_update_missing_professional_is_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()

    async def fake_update(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        "bcos_api.professionals.service.update_professional",
        fake_update,
    )

    with pytest.raises(ProfessionalNotFound):
        await update_tenant_professional(
            object(),  # type: ignore[arg-type]
            context=context,
            professional_id=uuid4(),
            external_user_id=None,
            name="Cristiana Valente",
            email=None,
            phone=None,
            status=ProfessionalStatus.ACTIVE,
        )


@pytest.mark.asyncio
async def test_professional_role_cannot_list_professionals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = professional_context()
    repository_called = False

    async def fake_list(*args: object, **kwargs: object) -> list[Professional]:
        nonlocal repository_called
        repository_called = True
        return []

    monkeypatch.setattr(
        "bcos_api.professionals.service.list_professionals",
        fake_list,
    )

    with pytest.raises(PermissionDenied):
        await list_tenant_professionals(
            object(),  # type: ignore[arg-type]
            context=context,
        )

    assert repository_called is False
