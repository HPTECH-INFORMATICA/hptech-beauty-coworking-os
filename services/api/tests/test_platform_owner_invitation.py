"""Tests for the explicit platform OWNER invitation contract."""

from uuid import uuid4

from bcos_api.platform.onboarding.schemas import OwnerInvitation, OwnerInvitationCreate


def test_owner_invitation_schema_is_fixed_to_owner_invited() -> None:
    tenant_id = uuid4()
    membership_id = uuid4()
    invitation = OwnerInvitation(
        membership_id=membership_id,
        tenant_id=tenant_id,
        external_user_id="owner-identity",
    )
    assert invitation.role == "OWNER"
    assert invitation.status == "INVITED"


def test_owner_invitation_create_forbids_extra_authority_fields() -> None:
    try:
        OwnerInvitationCreate.model_validate(
            {"external_user_id": "owner-identity", "role": "ADMIN"}
        )
    except ValueError:
        return
    raise AssertionError("Owner invitation input must not accept caller-selected role.")
