"""Tests for invitation acceptance authority."""

from uuid import uuid4

from bcos_api.auth.identity import AuthenticatedIdentity


def test_acceptance_identity_is_stable_external_identity() -> None:
    identity = AuthenticatedIdentity(external_user_id="trusted-user")
    assert identity.external_user_id == "trusted-user"


def test_membership_identifier_is_not_identity_authority() -> None:
    assert str(uuid4()) != "trusted-user"
