"""Contract tests for tenant-controlled professional self-onboarding."""
from pathlib import Path

from bcos_api.main import create_app


def test_self_onboarding_routes_are_exposed() -> None:
    paths = create_app().openapi()["paths"]
    assert "/api/v1/professional-onboarding/links" in paths
    assert "/api/v1/professional-onboarding/public/{slug}" in paths
    assert "/api/v1/professional-onboarding/requests" in paths
    assert "/api/v1/professional-onboarding/requests/{request_id}/approve" in paths


def test_public_registration_requires_current_platform_and_unit_documents() -> None:
    source = (Path(__file__).parents[1] / "src" / "bcos_api" / "professional_onboarding" / "router.py").read_text(encoding="utf-8")
    assert '{"PLATFORM_TERMS", "UNIT_POLICY"}' in source
    assert "ALL_CURRENT_ONBOARDING_DOCUMENTS_MUST_BE_ACCEPTED" in source
    assert "document_version" in source


def test_approval_creates_professional_before_access_invitation() -> None:
    source = (Path(__file__).parents[1] / "src" / "bcos_api" / "professional_onboarding" / "router.py").read_text(encoding="utf-8")
    professional = source.index("INSERT INTO professionals")
    invitation = source.index("INSERT INTO professional_access_invitations", professional)
    delivery = source.index("send_professional_access_invitation(", invitation)
    approved = source.index("status='APPROVED'", delivery)
    commit = source.index("await session.commit()", approved)
    assert professional < invitation < delivery < approved < commit


def test_self_onboarding_never_activates_tenant_or_membership() -> None:
    source = (Path(__file__).parents[1] / "src" / "bcos_api" / "professional_onboarding" / "router.py").read_text(encoding="utf-8")
    assert "INSERT INTO tenant_memberships" not in source
    assert "UPDATE tenants SET status" not in source


def test_professional_identity_can_have_multiple_tenant_relationships() -> None:
    migration = (Path(__file__).parents[3] / "database" / "migrations" / "versions" / "0012_professional_self_onboarding.py").read_text(encoding="utf-8")
    router = (Path(__file__).parents[1] / "src" / "bcos_api" / "professional_onboarding" / "router.py").read_text(encoding="utf-8")
    assert "UNIQUE (external_user_id)" not in migration
    assert "INSERT INTO tenant_memberships" not in router
    assert "UPDATE tenants SET status" not in router
