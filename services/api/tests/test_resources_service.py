"""Permanent M2 tests for the BCOS Resource application service."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from bcos_api.resource_categories.domain import ResourceCategory
from bcos_api.resources.domain import (
    InvalidResource,
    Resource,
    ResourceStatus,
)
from bcos_api.resources.service import (
    ResourceCategoryNotFound,
    ResourceNotFound,
    ResourceUnitNotFound,
    create_tenant_resource,
    get_tenant_resource,
    list_tenant_resources,
    update_tenant_resource,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.rbac import PermissionDenied
from bcos_api.units.domain import Unit


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


def unit_for(*, tenant_id: UUID, unit_id: UUID) -> Unit:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    return Unit(
        id=unit_id,
        tenant_id=tenant_id,
        name="Batel",
        timezone="America/Sao_Paulo",
        active=True,
        created_at=now,
        updated_at=now,
    )


def category_for(
    *,
    tenant_id: UUID,
    category_id: UUID,
) -> ResourceCategory:
    return ResourceCategory(
        id=category_id,
        tenant_id=tenant_id,
        name="Sala de Estetica",
        active=True,
    )


def resource_for(
    *,
    tenant_id: UUID,
    resource_id: UUID | None = None,
    unit_id: UUID | None = None,
    category_id: UUID | None = None,
) -> Resource:
    return Resource(
        id=resource_id or uuid4(),
        tenant_id=tenant_id,
        unit_id=unit_id or uuid4(),
        category_id=category_id or uuid4(),
        name="Sala 1",
        operational_status=ResourceStatus.AVAILABLE,
        buffer_before_minutes=10,
        buffer_after_minutes=15,
        active=True,
    )


@pytest.mark.asyncio
async def test_list_resources_uses_authorized_tenant_and_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()
    category_id = uuid4()
    expected = [resource_for(tenant_id=context.tenant_id)]

    async def fake_list_resources(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID | None,
        category_id: UUID | None,
    ) -> list[Resource]:
        del session
        assert tenant_id == context.tenant_id
        assert unit_id == expected_unit_id
        assert category_id == expected_category_id
        return expected

    expected_unit_id = unit_id
    expected_category_id = category_id

    monkeypatch.setattr(
        "bcos_api.resources.service.list_resources",
        fake_list_resources,
    )

    result = await list_tenant_resources(
        object(),  # type: ignore[arg-type]
        context=context,
        unit_id=unit_id,
        category_id=category_id,
    )

    assert result == expected


@pytest.mark.asyncio
async def test_get_resource_cannot_fall_back_to_another_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    resource_id = uuid4()

    async def fake_get_resource(
        session: object,
        *,
        tenant_id: UUID,
        resource_id: UUID,
    ) -> Resource | None:
        del session
        assert tenant_id == context.tenant_id
        assert resource_id == expected_resource_id
        return None

    expected_resource_id = resource_id

    monkeypatch.setattr(
        "bcos_api.resources.service.get_resource",
        fake_get_resource,
    )

    with pytest.raises(ResourceNotFound):
        await get_tenant_resource(
            object(),  # type: ignore[arg-type]
            context=context,
            resource_id=resource_id,
        )


@pytest.mark.asyncio
async def test_create_resource_validates_relations_in_authorized_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()
    category_id = uuid4()
    resource_id = uuid4()

    async def fake_get_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> Unit | None:
        del session
        assert tenant_id == context.tenant_id
        assert unit_id == expected_unit_id
        return unit_for(tenant_id=tenant_id, unit_id=unit_id)

    async def fake_get_category(
        session: object,
        *,
        tenant_id: UUID,
        category_id: UUID,
    ) -> ResourceCategory | None:
        del session
        assert tenant_id == context.tenant_id
        assert category_id == expected_category_id
        return category_for(
            tenant_id=tenant_id,
            category_id=category_id,
        )

    async def fake_create_resource(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
        category_id: UUID,
        name: str,
        buffer_before_minutes: int,
        buffer_after_minutes: int,
        active: bool,
    ) -> Resource:
        del session
        assert tenant_id == context.tenant_id
        assert unit_id == expected_unit_id
        assert category_id == expected_category_id
        assert name == "Sala 1"
        assert buffer_before_minutes == 10
        assert buffer_after_minutes == 15
        assert active is False

        return Resource(
            id=resource_id,
            tenant_id=tenant_id,
            unit_id=unit_id,
            category_id=category_id,
            name=name,
            operational_status=ResourceStatus.AVAILABLE,
            buffer_before_minutes=buffer_before_minutes,
            buffer_after_minutes=buffer_after_minutes,
            active=active,
        )

    expected_unit_id = unit_id
    expected_category_id = category_id

    monkeypatch.setattr(
        "bcos_api.resources.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.resources.service.get_resource_category",
        fake_get_category,
    )
    monkeypatch.setattr(
        "bcos_api.resources.service.create_resource",
        fake_create_resource,
    )

    result = await create_tenant_resource(
        object(),  # type: ignore[arg-type]
        context=context,
        unit_id=unit_id,
        category_id=category_id,
        name="  Sala 1  ",
        buffer_before_minutes=10,
        buffer_after_minutes=15,
        active=False,
    )

    assert result.id == resource_id
    assert result.tenant_id == context.tenant_id
    assert result.active is False


@pytest.mark.asyncio
async def test_create_rejects_unit_outside_authorized_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    category_lookup_called = False
    create_called = False

    async def fake_get_unit(*args: object, **kwargs: object) -> None:
        return None

    async def fake_get_category(
        *args: object,
        **kwargs: object,
    ) -> ResourceCategory | None:
        nonlocal category_lookup_called
        category_lookup_called = True
        return None

    async def fake_create(*args: object, **kwargs: object) -> Resource:
        nonlocal create_called
        create_called = True
        raise AssertionError("Create must not be called.")

    monkeypatch.setattr("bcos_api.resources.service.get_unit", fake_get_unit)
    monkeypatch.setattr(
        "bcos_api.resources.service.get_resource_category",
        fake_get_category,
    )
    monkeypatch.setattr(
        "bcos_api.resources.service.create_resource",
        fake_create,
    )

    with pytest.raises(ResourceUnitNotFound):
        await create_tenant_resource(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=uuid4(),
            category_id=uuid4(),
            name="Sala 1",
            buffer_before_minutes=0,
            buffer_after_minutes=0,
            active=True,
        )

    assert category_lookup_called is False
    assert create_called is False


@pytest.mark.asyncio
async def test_create_rejects_category_outside_authorized_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()
    create_called = False

    async def fake_get_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> Unit:
        del session
        return unit_for(tenant_id=tenant_id, unit_id=unit_id)

    async def fake_get_category(*args: object, **kwargs: object) -> None:
        return None

    async def fake_create(*args: object, **kwargs: object) -> Resource:
        nonlocal create_called
        create_called = True
        raise AssertionError("Create must not be called.")

    monkeypatch.setattr("bcos_api.resources.service.get_unit", fake_get_unit)
    monkeypatch.setattr(
        "bcos_api.resources.service.get_resource_category",
        fake_get_category,
    )
    monkeypatch.setattr(
        "bcos_api.resources.service.create_resource",
        fake_create,
    )

    with pytest.raises(ResourceCategoryNotFound):
        await create_tenant_resource(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=unit_id,
            category_id=uuid4(),
            name="Sala 1",
            buffer_before_minutes=0,
            buffer_after_minutes=0,
            active=True,
        )

    assert create_called is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "before", "after"),
    [
        ("", 0, 0),
        ("   ", 0, 0),
        ("Sala 1", -1, 0),
        ("Sala 1", 0, -1),
    ],
)
async def test_create_rejects_invalid_domain_data_before_relation_lookup(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    before: int,
    after: int,
) -> None:
    context = owner_context()
    relation_called = False

    async def fake_get_unit(*args: object, **kwargs: object) -> None:
        nonlocal relation_called
        relation_called = True
        return None

    monkeypatch.setattr("bcos_api.resources.service.get_unit", fake_get_unit)

    with pytest.raises(InvalidResource):
        await create_tenant_resource(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=uuid4(),
            category_id=uuid4(),
            name=name,
            buffer_before_minutes=before,
            buffer_after_minutes=after,
            active=True,
        )

    assert relation_called is False


@pytest.mark.asyncio
async def test_update_is_tenant_scoped_and_preserves_validated_relations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    resource_id = uuid4()
    unit_id = uuid4()
    category_id = uuid4()

    async def fake_get_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> Unit:
        del session
        assert tenant_id == context.tenant_id
        return unit_for(tenant_id=tenant_id, unit_id=unit_id)

    async def fake_get_category(
        session: object,
        *,
        tenant_id: UUID,
        category_id: UUID,
    ) -> ResourceCategory:
        del session
        assert tenant_id == context.tenant_id
        return category_for(
            tenant_id=tenant_id,
            category_id=category_id,
        )

    async def fake_update_resource(
        session: object,
        *,
        tenant_id: UUID,
        resource_id: UUID,
        unit_id: UUID,
        category_id: UUID,
        name: str,
        operational_status: ResourceStatus,
        buffer_before_minutes: int,
        buffer_after_minutes: int,
        active: bool,
    ) -> Resource:
        del session
        assert tenant_id == context.tenant_id
        assert resource_id == expected_resource_id
        assert unit_id == expected_unit_id
        assert category_id == expected_category_id
        assert name == "Sala Premium"
        assert operational_status is ResourceStatus.MAINTENANCE
        assert buffer_before_minutes == 5
        assert buffer_after_minutes == 20
        assert active is True

        return Resource(
            id=resource_id,
            tenant_id=tenant_id,
            unit_id=unit_id,
            category_id=category_id,
            name=name,
            operational_status=operational_status,
            buffer_before_minutes=buffer_before_minutes,
            buffer_after_minutes=buffer_after_minutes,
            active=active,
        )

    expected_resource_id = resource_id
    expected_unit_id = unit_id
    expected_category_id = category_id

    monkeypatch.setattr("bcos_api.resources.service.get_unit", fake_get_unit)
    monkeypatch.setattr(
        "bcos_api.resources.service.get_resource_category",
        fake_get_category,
    )
    monkeypatch.setattr(
        "bcos_api.resources.service.update_resource",
        fake_update_resource,
    )

    result = await update_tenant_resource(
        object(),  # type: ignore[arg-type]
        context=context,
        resource_id=resource_id,
        unit_id=unit_id,
        category_id=category_id,
        name="  Sala Premium  ",
        operational_status=ResourceStatus.MAINTENANCE,
        buffer_before_minutes=5,
        buffer_after_minutes=20,
        active=True,
    )

    assert result.id == resource_id
    assert result.tenant_id == context.tenant_id
    assert result.name == "Sala Premium"


@pytest.mark.asyncio
async def test_update_missing_resource_is_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = owner_context()
    unit_id = uuid4()
    category_id = uuid4()

    async def fake_get_unit(
        session: object,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> Unit:
        del session
        return unit_for(tenant_id=tenant_id, unit_id=unit_id)

    async def fake_get_category(
        session: object,
        *,
        tenant_id: UUID,
        category_id: UUID,
    ) -> ResourceCategory:
        del session
        return category_for(
            tenant_id=tenant_id,
            category_id=category_id,
        )

    async def fake_update(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr("bcos_api.resources.service.get_unit", fake_get_unit)
    monkeypatch.setattr(
        "bcos_api.resources.service.get_resource_category",
        fake_get_category,
    )
    monkeypatch.setattr(
        "bcos_api.resources.service.update_resource",
        fake_update,
    )

    with pytest.raises(ResourceNotFound):
        await update_tenant_resource(
            object(),  # type: ignore[arg-type]
            context=context,
            resource_id=uuid4(),
            unit_id=unit_id,
            category_id=category_id,
            name="Sala 1",
            operational_status=ResourceStatus.AVAILABLE,
            buffer_before_minutes=0,
            buffer_after_minutes=0,
            active=True,
        )


@pytest.mark.asyncio
async def test_professional_role_cannot_list_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = professional_context()
    repository_called = False

    async def fake_list(*args: object, **kwargs: object) -> list[Resource]:
        nonlocal repository_called
        repository_called = True
        return []

    monkeypatch.setattr("bcos_api.resources.service.list_resources", fake_list)

    with pytest.raises(PermissionDenied):
        await list_tenant_resources(
            object(),  # type: ignore[arg-type]
            context=context,
        )

    assert repository_called is False
