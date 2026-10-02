"""Contract tests for professional email-first onboarding."""
from pathlib import Path
from bcos_api.main import create_app

def test_professional_invitation_routes_are_exposed() -> None:
    schema = create_app().openapi()
    assert "/api/v1/professional-invitations" in schema["paths"]
    assert "/api/v1/professional-invitations/{invitation_id}/accept" in schema["paths"]
    assert "/api/v1/professional-invitations/professionals/{professional_id}" in schema["paths"]

def test_professional_acceptance_binds_trusted_identity_and_membership() -> None:
    source = (Path(__file__).parents[1] / "src" / "bcos_api" / "professional_invitations" / "router.py").read_text(encoding="utf-8")
    assert 'neon_auth."user"' in source
    assert "lower(i.email)=:email" in source
    assert "'PROFESSIONAL','ACTIVE'" in source
    assert "SET external_user_id=:external_user_id" in source
    assert "PROFESSIONAL_ACCESS_ACCEPTED" in source

def test_professional_invitation_never_changes_tenant_commercial_status() -> None:
    source = (Path(__file__).parents[1] / "src" / "bcos_api" / "professional_invitations" / "router.py").read_text(encoding="utf-8")
    assert "update_contracting_tenant_status" not in source
    assert "PENDING_ACTIVATION" not in source
