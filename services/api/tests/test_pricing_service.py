"""Permanent M6 tests for the BCOS Pricing application service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from bcos_api.pricing.domain import InvalidPricingRule, PricingRule, PricingRuleStatus
from bcos_api.pricing.service import (
    PricingRuleResourceCategoryNotFound,
    PricingRuleUnitNotFound,
    create_tenant_pricing_rule,
    list_tenant_pricing_rules,
)
from bcos_api.resource_categories.domain import ResourceCategory
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.rbac import PermissionDenied
from bcos_api.units.domain import Unit


def context_for(
    role: MembershipRole,
    *,
    tenant_id: UUID | None = None,
) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id or uuid4(),
        membership_id=uuid4(),
        external_user_id=f"identity-{role.value.lower()}",
        role=role,
    )


def pricing_rule_for(*, tenant_id: UUID) -> PricingRule:
    now = datetime.now(UTC)

    return PricingRule(
        id=uuid4(),
        tenant_id=tenant_id,
        unit_id=None,
        resource_category_id=None,
        name="Tabela padrão",
        status=PricingRuleStatus.ACTIVE,
        priority=100,
        currency="BRL",
        rule_definition={"kind": "opaque-test-definition"},
        valid_from=None,
        valid_until=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def unit_for(*, tenant_id: UUID, unit_id: UUID) -> Unit:
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
        name="Sala de Estética",
        active=True,
    )


@pytest.mark.asyncio
async def test_list_pricing_rules_uses_authorized_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = context_for(MembershipRole.OWNER)
    expected = [pricing_rule_for(tenant_id=context.tenant_id)]

    async def fake_list(
        session: object,
        *,
        tenant_id: UUID,
    ) -> list[PricingRule]:
        del session
        assert tenant_id == context.tenant_id
        return expected

    monkeypatch.setattr(
        "bcos_api.pricing.service.list_pricing_rules",
        fake_list,
    )

    result = await list_tenant_pricing_rules(
        object(),  # type: ignore[arg-type]
        context=context,
    )

    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        MembershipRole.RECEPTION,
        MembershipRole.PROFESSIONAL,
    ],
)
async def test_non_admin_role_cannot_list_pricing_rules(
    monkeypatch: pytest.MonkeyPatch,
    role: MembershipRole,
) -> None:
    repository_called = False

    async def fake_list(*args: object, **kwargs: object) -> list[PricingRule]:
        nonlocal repository_called
        repository_called = True
        return []

    monkeypatch.setattr(
        "bcos_api.pricing.service.list_pricing_rules",
        fake_list,
    )

    with pytest.raises(PermissionDenied):
        await list_tenant_pricing_rules(
            object(),  # type: ignore[arg-type]
            context=context_for(role),
        )

    assert repository_called is False


@pytest.mark.asyncio
async def test_admin_can_list_pricing_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = context_for(MembershipRole.ADMIN)

    async def fake_list(
        session: object,
        *,
        tenant_id: UUID,
    ) -> list[PricingRule]:
        del session
        assert tenant_id == context.tenant_id
        return []

    monkeypatch.setattr(
        "bcos_api.pricing.service.list_pricing_rules",
        fake_list,
    )

    assert (
        await list_tenant_pricing_rules(
            object(),  # type: ignore[arg-type]
            context=context,
        )
        == []
    )


@pytest.mark.asyncio
async def test_create_pricing_rule_validates_relations_in_authorized_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = context_for(MembershipRole.OWNER)
    unit_id = uuid4()
    category_id = uuid4()
    captured: dict[str, object] = {}

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

    async def fake_create(
        session: object,
        **kwargs: Any,
    ) -> PricingRule:
        del session
        captured.update(kwargs)
        return pricing_rule_for(tenant_id=context.tenant_id)

    monkeypatch.setattr(
        "bcos_api.pricing.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.pricing.service.get_resource_category",
        fake_get_category,
    )
    monkeypatch.setattr(
        "bcos_api.pricing.service.create_pricing_rule",
        fake_create,
    )

    result = await create_tenant_pricing_rule(
        object(),  # type: ignore[arg-type]
        context=context,
        unit_id=unit_id,
        resource_category_id=category_id,
        name="  Tabela Batel  ",
        priority=10,
        currency="BRL",
        rule_definition={"opaque": {"value": 1}},
        valid_from=None,
        valid_until=None,
    )

    assert result.tenant_id == context.tenant_id
    assert captured["tenant_id"] == context.tenant_id
    assert captured["unit_id"] == unit_id
    assert captured["resource_category_id"] == category_id
    assert captured["name"] == "Tabela Batel"
    assert captured["priority"] == 10
    assert captured["currency"] == "BRL"
    assert captured["rule_definition"] == {"opaque": {"value": 1}}


@pytest.mark.asyncio
async def test_create_rejects_unit_outside_authorized_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = context_for(MembershipRole.OWNER)
    category_lookup_called = False
    create_called = False

    async def fake_get_unit(*args: object, **kwargs: object) -> None:
        return None

    async def fake_get_category(
        *args: object,
        **kwargs: object,
    ) -> None:
        nonlocal category_lookup_called
        category_lookup_called = True
        return None

    async def fake_create(*args: object, **kwargs: object) -> PricingRule:
        nonlocal create_called
        create_called = True
        raise AssertionError("Create must not be called.")

    monkeypatch.setattr(
        "bcos_api.pricing.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.pricing.service.get_resource_category",
        fake_get_category,
    )
    monkeypatch.setattr(
        "bcos_api.pricing.service.create_pricing_rule",
        fake_create,
    )

    with pytest.raises(PricingRuleUnitNotFound):
        await create_tenant_pricing_rule(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=uuid4(),
            resource_category_id=uuid4(),
            name="Tabela",
            priority=100,
            currency="BRL",
            rule_definition={"opaque": True},
            valid_from=None,
            valid_until=None,
        )

    assert category_lookup_called is False
    assert create_called is False


@pytest.mark.asyncio
async def test_create_rejects_category_outside_authorized_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = context_for(MembershipRole.OWNER)
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

    async def fake_create(*args: object, **kwargs: object) -> PricingRule:
        nonlocal create_called
        create_called = True
        raise AssertionError("Create must not be called.")

    monkeypatch.setattr(
        "bcos_api.pricing.service.get_unit",
        fake_get_unit,
    )
    monkeypatch.setattr(
        "bcos_api.pricing.service.get_resource_category",
        fake_get_category,
    )
    monkeypatch.setattr(
        "bcos_api.pricing.service.create_pricing_rule",
        fake_create,
    )

    with pytest.raises(PricingRuleResourceCategoryNotFound):
        await create_tenant_pricing_rule(
            object(),  # type: ignore[arg-type]
            context=context,
            unit_id=unit_id,
            resource_category_id=uuid4(),
            name="Tabela",
            priority=100,
            currency="BRL",
            rule_definition={"opaque": True},
            valid_from=None,
            valid_until=None,
        )

    assert create_called is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "priority", "currency"),
    [
        ("", 100, "BRL"),
        ("   ", 100, "BRL"),
        ("Tabela", -1, "BRL"),
        ("Tabela", 100, "USD"),
    ],
)
async def test_create_rejects_invalid_contract_before_relation_lookup(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    priority: int,
    currency: str,
) -> None:
    relation_called = False

    async def fake_get_unit(*args: object, **kwargs: object) -> None:
        nonlocal relation_called
        relation_called = True
        return None

    monkeypatch.setattr(
        "bcos_api.pricing.service.get_unit",
        fake_get_unit,
    )

    with pytest.raises(InvalidPricingRule):
        await create_tenant_pricing_rule(
            object(),  # type: ignore[arg-type]
            context=context_for(MembershipRole.OWNER),
            unit_id=uuid4(),
            resource_category_id=None,
            name=name,
            priority=priority,
            currency=currency,  # type: ignore[arg-type]
            rule_definition={"opaque": True},
            valid_from=None,
            valid_until=None,
        )

    assert relation_called is False


@pytest.mark.asyncio
async def test_create_rejects_invalid_validity_window_before_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_called = False
    now = datetime.now(UTC)

    async def fake_create(*args: object, **kwargs: object) -> PricingRule:
        nonlocal repository_called
        repository_called = True
        raise AssertionError("Create must not be called.")

    monkeypatch.setattr(
        "bcos_api.pricing.service.create_pricing_rule",
        fake_create,
    )

    with pytest.raises(InvalidPricingRule):
        await create_tenant_pricing_rule(
            object(),  # type: ignore[arg-type]
            context=context_for(MembershipRole.OWNER),
            unit_id=None,
            resource_category_id=None,
            name="Tabela",
            priority=100,
            currency="BRL",
            rule_definition={"opaque": True},
            valid_from=now,
            valid_until=now - timedelta(minutes=1),
        )

    assert repository_called is False
