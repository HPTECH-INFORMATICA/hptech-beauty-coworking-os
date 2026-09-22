"""Tenant membership administration domain."""

from __future__ import annotations

from bcos_api.tenancy.membership import MembershipRole, MembershipStatus, TenantMembership


class InvalidMembershipAdministration(ValueError):
    """Raised when a membership administration command is invalid."""


def validate_invited_role(*, actor_role: MembershipRole, invited_role: MembershipRole) -> None:
    if invited_role is MembershipRole.OWNER:
        raise InvalidMembershipAdministration("OWNER invitation requires ownership-transfer authority.")
    if actor_role not in {MembershipRole.OWNER, MembershipRole.ADMIN}:
        raise InvalidMembershipAdministration("Role cannot administer tenant memberships.")


def validate_membership_status(status: MembershipStatus) -> None:
    if status not in {MembershipStatus.ACTIVE, MembershipStatus.INACTIVE}:
        raise InvalidMembershipAdministration("Membership status can only become ACTIVE or INACTIVE.")


__all__ = ["InvalidMembershipAdministration", "TenantMembership", "validate_invited_role", "validate_membership_status"]
