"""Permanent M2 tests for the BCOS Resource Category application service."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from bcos_api.resource_categories.domain import (
    InvalidResourceCategory,
    ResourceCategory,
)
from bcos_api.resource_categories.service import (
    create_tenant_resource_category,
    list_tenant_resource_categories,
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


def professional_context(
    *,
    tenant_id: UUID | None = None,
) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id or uuid4(),
        membership_id=uuid4(),
        external_user_id="identity-professional",
        role=MembershipRole.PROFESSIONAL,
    )


def category_for(
    *,
    tenant_id: UUID,
    name: str = "Sala de Estetica",
    active: bool = True,
) -> ResourceCategory:
    return ResourceCategory(
        id=uuid4(),
        tenant_id=tenant_id,
        name=name,
        active=active,
    )


@pytest.mark.asyncio
async def test_list_categories_uses_only_authorized_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    expected = [category_for(tenant_id=context.tenant_id)]
    captured_tenant_id: UUID | None = None

    async def fake_list_resource_categories(
        session: object,
        *,
        tenant_id: UUID,
    ) -> list[ResourceCategory]:
        nonlocal captured_tenant_id
        del session

        captured_tenant_id = tenant_id
        return expected

    monkeypatch.setattr(
        "bcos_api.resource_categories.service.list_resource_categories",
        fake_list_resource_categories,
    )

    result = await list_tenant_resource_categories(
        object(),  # type: ignore[arg-type]
        context=context,
    )

    assert result == expected
    assert captured_tenant_id == context.tenant_id


@pytest.mark.asyncio
async def test_create_category_uses_context_tenant_and_normalized_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    created_id = uuid4()

    async def fake_create_resource_category(
        session: object,
        *,
        tenant_id: UUID,
        name: str,
        active: bool,
    ) -> ResourceCategory:
        del session

        assert tenant_id == context.tenant_id
        assert name == "Sala de Estetica"
        assert active is False

        return ResourceCategory(
            id=created_id,
            tenant_id=tenant_id,
            name=name,
            active=active,
        )

    monkeypatch.setattr(
        "bcos_api.resource_categories.service.create_resource_category",
        fake_create_resource_category,
    )

    result = await create_tenant_resource_category(
        object(),  # type: ignore[arg-type]
        context=context,
        name="  Sala de Estetica  ",
        active=False,
    )

    assert result.id == created_id
    assert result.tenant_id == context.tenant_id
    assert result.name == "Sala de Estetica"
    assert result.active is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name",
    [
        "",
        "   ",
    ],
)
async def test_create_category_rejects_blank_name_before_repository(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
) -> None:
    context = owner_context()
    repository_called = False

    async def fake_create_resource_category(
        *args: object,
        **kwargs: object,
    ) -> ResourceCategory:
        nonlocal repository_called
        repository_called = True
        raise AssertionError("Repository must not be called.")

    monkeypatch.setattr(
        "bcos_api.resource_categories.service.create_resource_category",
        fake_create_resource_category,
    )

    with pytest.raises(InvalidResourceCategory):
        await create_tenant_resource_category(
            object(),  # type: ignore[arg-type]
            context=context,
            name=name,
            active=True,
        )

    assert repository_called is False


@pytest.mark.asyncio
async def test_create_category_rejects_name_over_database_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    repository_called = False

    async def fake_create_resource_category(
        *args: object,
        **kwargs: object,
    ) -> ResourceCategory:
        nonlocal repository_called
        repository_called = True
        raise AssertionError("Repository must not be called.")

    monkeypatch.setattr(
        "bcos_api.resource_categories.service.create_resource_category",
        fake_create_resource_category,
    )

    with pytest.raises(InvalidResourceCategory):
        await create_tenant_resource_category(
            object(),  # type: ignore[arg-type]
            context=context,
            name="X" * 121,
            active=True,
        )

    assert repository_called is False


@pytest.mark.asyncio
async def test_professional_role_cannot_list_resource_categories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = professional_context()
    repository_called = False

    async def fake_list_resource_categories(
        *args: object,
        **kwargs: object,
    ) -> list[ResourceCategory]:
        nonlocal repository_called
        repository_called = True
        return []

    monkeypatch.setattr(
        "bcos_api.resource_categories.service.list_resource_categories",
        fake_list_resource_categories,
    )

    with pytest.raises(PermissionDenied):
        await list_tenant_resource_categories(
            object(),  # type: ignore[arg-type]
            context=context,
        )

    assert repository_called is False


@pytest.mark.asyncio
async def test_professional_role_cannot_create_resource_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = professional_context()
    repository_called = False

    async def fake_create_resource_category(
        *args: object,
        **kwargs: object,
    ) -> ResourceCategory:
        nonlocal repository_called
        repository_called = True
        raise AssertionError("Repository must not be called.")

    monkeypatch.setattr(
        "bcos_api.resource_categories.service.create_resource_category",
        fake_create_resource_category,
    )

    with pytest.raises(PermissionDenied):
        await create_tenant_resource_category(
            object(),  # type: ignore[arg-type]
            context=context,
            name="Sala de Estetica",
            active=True,
        )

    assert repository_called is False
