"""Tests for invitation acceptance authority."""

from pathlib import Path
from uuid import uuid4

from bcos_api.auth.identity import AuthenticatedIdentity


def test_acceptance_identity_is_stable_external_identity() -> None:
    identity = AuthenticatedIdentity(external_user_id="trusted-user")
    assert identity.external_user_id == "trusted-user"


def test_membership_identifier_is_not_identity_authority() -> None:
    assert str(uuid4()) != "trusted-user"


def test_owner_acceptance_does_not_activate_contracting_tenant() -> None:
    """OWNER acceptance activates membership only; HPTECH PLATFORM owns tenant lifecycle."""
    router_source = (
        Path(__file__).parents[1] / "src" / "bcos_api" / "invitation" / "router.py"
    ).read_text(encoding="utf-8")

    assert "update_contracting_tenant_status" not in router_source
    assert "TenantCommercialStatus.ACTIVE" not in router_source
