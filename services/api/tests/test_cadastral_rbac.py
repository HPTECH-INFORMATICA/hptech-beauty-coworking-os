"""Regression tests for tenant-managed cadastral RBAC."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from bcos_api.access.router import _tenant_destination
from bcos_api.admin.access_roles_router import _permissions
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.rbac import Permission


def _context(
    role: MembershipRole,
    permissions: frozenset[Permission],
) -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        membership_id=uuid4(),
        external_user_id="rbac-test-user",
        role=role,
        permissions=permissions,
    )


def test_destination_is_driven_by_effective_permissions() -> None:
    assert _tenant_destination(
        MembershipRole.RECEPTION,
        {Permission.ADMIN_VIEW},
    ) == "/administracao"
    assert _tenant_destination(
        MembershipRole.RECEPTION,
        {Permission.PROFESSIONAL_OWN},
    ) == "/profissional"
    assert _tenant_destination(
        MembershipRole.PROFESSIONAL,
        {Permission.AGENDA_VIEW},
    ) == "/"


def test_owner_can_compose_any_customer_role_permissions() -> None:
    context = _context(
        MembershipRole.OWNER,
        frozenset({Permission.ROLE_MANAGE}),
    )
    assert _permissions(
        ["ROLE_MANAGE", "FINANCE_VIEW", "USER_ADMIN"],
        context=context,
    ) == ["FINANCE_VIEW", "ROLE_MANAGE", "USER_ADMIN"]


def test_delegated_role_manager_cannot_grant_permissions_it_does_not_have() -> None:
    context = _context(
        MembershipRole.RECEPTION,
        frozenset({Permission.ROLE_MANAGE}),
    )
    with pytest.raises(HTTPException) as exc_info:
        _permissions(
            ["ROLE_MANAGE", "FINANCE_VIEW"],
            context=context,
        )
    assert exc_info.value.status_code == 403
