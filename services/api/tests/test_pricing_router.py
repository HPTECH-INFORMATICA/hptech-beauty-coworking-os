from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from bcos_api.db.session import get_async_session
from bcos_api.main import create_app
from bcos_api.pricing.domain import (
    InvalidPricingRule,
    PricingRule,
    PricingRuleStatus,
)
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.tenancy.membership import MembershipRole


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def make_context(tenant_id: UUID) -> TenantContext:
    return TenantContext(
        tenant_id=tenant_id,
        membership_id=uuid4(),
        external_user_id="identity:test-owner",
        role=MembershipRole.OWNER,
    )


def make_rule(
    *,
    tenant_id: UUID,
    unit_id: UUID | None = None,
    resource_category_id: UUID | None = None,
) -> PricingRule:
    now = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)

    return PricingRule(
        id=uuid4(),
        tenant_id=tenant_id,
        unit_id=unit_id,
        resource_category_id=resource_category_id,
        name="Regra principal",
        status=PricingRuleStatus.ACTIVE,
        priority=10,
        currency="BRL",
        rule_definition={"opaque_contract": {"mode": "configured"}},
        valid_from=None,
        valid_until=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def create_test_app(
    *,
    session: FakeSession,
    context: TenantContext,
):
    app = create_app()

    async def fake_session_dependency():
        yield session

    async def fake_tenant_context() -> TenantContext:
        return context

    app.dependency_overrides[get_async_session] = fake_session_dependency
    app.dependency_overrides[get_tenant_context] = fake_tenant_context

    return app


def test_list_pricing_rules_returns_tenant_rules(monkeypatch) -> None:
    tenant_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    rule = make_rule(tenant_id=tenant_id)

    captured: dict[str, object] = {}

    async def fake_list_tenant_pricing_rules(
        received_session,
        *,
        context,
    ):
        captured["session"] = received_session
        captured["context"] = context
        return [rule]

    monkeypatch.setattr(
        "bcos_api.pricing.router.list_tenant_pricing_rules",
        fake_list_tenant_pricing_rules,
    )

    client = TestClient(create_test_app(session=session, context=context))
    response = client.get("/api/v1/pricing-rules")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(rule.id),
            "unit_id": None,
            "resource_category_id": None,
            "name": "Regra principal",
            "status": "ACTIVE",
            "priority": 10,
            "currency": "BRL",
            "rule_definition": {"opaque_contract": {"mode": "configured"}},
            "valid_from": None,
            "valid_until": None,
        }
    ]
    assert captured["session"] is session
    assert captured["context"] is context
    assert session.commits == 0
    assert session.rollbacks == 0


def test_create_pricing_rule_returns_201_and_commits(monkeypatch) -> None:
    tenant_id = uuid4()
    unit_id = uuid4()
    resource_category_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)
    rule = make_rule(
        tenant_id=tenant_id,
        unit_id=unit_id,
        resource_category_id=resource_category_id,
    )

    captured: dict[str, object] = {}

    async def fake_create_tenant_pricing_rule(
        received_session,
        **kwargs,
    ):
        captured["session"] = received_session
        captured.update(kwargs)
        return rule

    monkeypatch.setattr(
        "bcos_api.pricing.router.create_tenant_pricing_rule",
        fake_create_tenant_pricing_rule,
    )

    client = TestClient(create_test_app(session=session, context=context))
    response = client.post(
        "/api/v1/pricing-rules",
        json={
            "unit_id": str(unit_id),
            "resource_category_id": str(resource_category_id),
            "name": "Regra principal",
            "priority": 10,
            "currency": "BRL",
            "rule_definition": {
                "opaque_contract": {
                    "mode": "configured",
                }
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == str(rule.id)
    assert response.json()["currency"] == "BRL"
    assert response.json()["rule_definition"] == {
        "opaque_contract": {"mode": "configured"}
    }

    assert captured["session"] is session
    assert captured["context"] is context
    assert captured["unit_id"] == unit_id
    assert captured["resource_category_id"] == resource_category_id
    assert captured["name"] == "Regra principal"
    assert captured["priority"] == 10
    assert captured["currency"] == "BRL"
    assert captured["valid_from"] is None
    assert captured["valid_until"] is None
    assert session.commits == 1
    assert session.rollbacks == 0


def test_create_pricing_rule_domain_error_returns_422_and_rolls_back(
    monkeypatch,
) -> None:
    tenant_id = uuid4()
    session = FakeSession()
    context = make_context(tenant_id)

    async def fake_create_tenant_pricing_rule(*args, **kwargs):
        raise InvalidPricingRule("Pricing rule is invalid.")

    monkeypatch.setattr(
        "bcos_api.pricing.router.create_tenant_pricing_rule",
        fake_create_tenant_pricing_rule,
    )

    client = TestClient(create_test_app(session=session, context=context))
    response = client.post(
        "/api/v1/pricing-rules",
        json={
            "name": "Regra inválida",
            "rule_definition": {"opaque_contract": {}},
        },
    )

    assert response.status_code == 422
    assert session.commits == 0
    assert session.rollbacks == 1
