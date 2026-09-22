"""Tests for tenant membership administration rules."""

import pytest

from bcos_api.admin.domain import (
    InvalidMembershipAdministration,
    validate_invited_role,
    validate_membership_status,
)
from bcos_api.tenancy.membership import MembershipRole, MembershipStatus


@pytest.mark.parametrize("actor", [MembershipRole.OWNER, MembershipRole.ADMIN])
@pytest.mark.parametrize("invited", [MembershipRole.ADMIN, MembershipRole.RECEPTION, MembershipRole.PROFESSIONAL])
def test_owner_and_admin_can_invite_non_owner_roles(actor: MembershipRole, invited: MembershipRole) -> None:
    validate_invited_role(actor_role=actor, invited_role=invited)


@pytest.mark.parametrize("actor", [MembershipRole.RECEPTION, MembershipRole.PROFESSIONAL])
def test_operational_roles_cannot_administer_memberships(actor: MembershipRole) -> None:
    with pytest.raises(InvalidMembershipAdministration):
        validate_invited_role(actor_role=actor, invited_role=MembershipRole.RECEPTION)


@pytest.mark.parametrize("actor", list(MembershipRole))
def test_owner_cannot_be_created_by_regular_tenant_invitation(actor: MembershipRole) -> None:
    with pytest.raises(InvalidMembershipAdministration):
        validate_invited_role(actor_role=actor, invited_role=MembershipRole.OWNER)


@pytest.mark.parametrize("status", [MembershipStatus.ACTIVE, MembershipStatus.INACTIVE])
def test_membership_status_mutations_are_explicit(status: MembershipStatus) -> None:
    validate_membership_status(status)


def test_invited_status_cannot_be_reapplied_by_status_endpoint() -> None:
    with pytest.raises(InvalidMembershipAdministration):
        validate_membership_status(MembershipStatus.INVITED)
