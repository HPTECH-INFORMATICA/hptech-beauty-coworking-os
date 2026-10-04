"""Tenant-managed role administration.

Roles are business data owned by each tenant. BCOS only owns the permission
catalog because it describes executable product capabilities.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bcos_api.audit.repository import create_audit_log
from bcos_api.db.session import get_async_session
from bcos_api.tenancy.context import TenantContext
from bcos_api.tenancy.dependencies import get_tenant_context
from bcos_api.tenancy.membership import MembershipRole
from bcos_api.tenancy.rbac import Permission, PermissionDenied, has_permission, require_permission

router = APIRouter(prefix="/api/v1/admin/access-roles", tags=["Tenant Access Roles"])
SessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
TenantContextDependency = Annotated[TenantContext, Depends(get_tenant_context)]

# Product capabilities are technical contracts, not customer roles.
# Tenant customers compose any role they want from this catalog.
PERMISSION_CATALOG: tuple[dict[str, str], ...] = (
    {"code":"DASHBOARD_VIEW","module":"Visão geral","action":"Visualizar"},
    {"code":"AGENDA_VIEW","module":"Agenda","action":"Visualizar"},
    {"code":"AGENDA_CREATE","module":"Agenda","action":"Criar"},
    {"code":"AGENDA_EDIT","module":"Agenda","action":"Editar"},
    {"code":"AGENDA_DELETE","module":"Agenda","action":"Excluir"},
    {"code":"AGENDA_MANAGE","module":"Agenda","action":"Gerenciar"},
    {"code":"AVAILABILITY_VIEW","module":"Disponibilidade","action":"Visualizar"},
    {"code":"CHECKIN_VIEW","module":"Check-in e uso","action":"Visualizar"},
    {"code":"CHECKIN_MANAGE","module":"Check-in e uso","action":"Gerenciar"},
    {"code":"FINANCE_VIEW","module":"Financeiro","action":"Visualizar"},
    {"code":"FINANCE_CREATE","module":"Financeiro","action":"Criar"},
    {"code":"FINANCE_EDIT","module":"Financeiro","action":"Editar"},
    {"code":"FINANCE_DELETE","module":"Financeiro","action":"Excluir"},
    {"code":"FINANCE_MANAGE","module":"Financeiro","action":"Gerenciar"},
    {"code":"ADMIN_VIEW","module":"Administração","action":"Visualizar"},
    {"code":"ADMIN_CONFIG","module":"Administração","action":"Editar configurações"},
    {"code":"USER_VIEW","module":"Usuários e acessos","action":"Visualizar"},
    {"code":"USER_CREATE","module":"Usuários e acessos","action":"Criar/convidar"},
    {"code":"USER_EDIT","module":"Usuários e acessos","action":"Editar"},
    {"code":"USER_BLOCK","module":"Usuários e acessos","action":"Bloquear/reativar"},
    {"code":"USER_DELETE","module":"Usuários e acessos","action":"Remover acesso"},
    {"code":"ROLE_MANAGE","module":"Usuários e acessos","action":"Gerenciar papéis"},
    {"code":"USER_ADMIN","module":"Usuários e acessos","action":"Gerenciar acessos"},
    {"code":"PROFESSIONAL_OWN","module":"Portal profissional","action":"Acessar próprio portal"},
)
EDITABLE_PERMISSIONS = frozenset(item["code"] for item in PERMISSION_CATALOG)


class AccessRoleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    permissions: list[str] = Field(default_factory=list)


class AccessRoleUpdate(AccessRoleCreate):
    active: bool = True


class MembershipAccessRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    access_role_id: UUID


class AccessRoleResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    active: bool
    permissions: list[str]
    assigned_users: int


def _permissions(values: list[str], *, context: TenantContext) -> list[str]:
    requested = {value.strip() for value in values}
    invalid = requested - EDITABLE_PERMISSIONS
    if invalid:
        raise HTTPException(status_code=422, detail=f"Permissões inválidas: {', '.join(sorted(invalid))}")
    if context.role is not MembershipRole.OWNER:
        actor_permissions = {
            permission.value
            for permission in (context.permissions or frozenset())
            if isinstance(permission, Permission)
        }
        forbidden = requested - actor_permissions
        if forbidden:
            raise HTTPException(
                status_code=403,
                detail="Não é permitido conceder permissões que o próprio usuário não possui.",
            )
    return sorted(requested)


async def _replace_permissions(session: AsyncSession, *, tenant_id: UUID, role_id: UUID, permissions: list[str]) -> None:
    await session.execute(text("DELETE FROM tenant_access_role_permissions WHERE tenant_id=:tenant_id AND role_id=:role_id"), {"tenant_id": tenant_id, "role_id": role_id})
    for permission in permissions:
        await session.execute(text("""INSERT INTO tenant_access_role_permissions
            (tenant_id,role_id,permission,granted) VALUES (:tenant_id,:role_id,:permission,TRUE)"""),
            {"tenant_id": tenant_id, "role_id": role_id, "permission": permission})


@router.get("/catalog")
async def permission_catalog(context: TenantContextDependency) -> dict[str, object]:
    require_permission(context, Permission.ROLE_MANAGE)
    return {"permissions": PERMISSION_CATALOG}


@router.get("", response_model=list[AccessRoleResponse])
async def list_roles(session: SessionDependency, context: TenantContextDependency) -> list[AccessRoleResponse]:
    if not any(
        has_permission(context, permission)
        for permission in (Permission.USER_VIEW, Permission.USER_CREATE, Permission.USER_ADMIN, Permission.ROLE_MANAGE)
    ):
        raise PermissionDenied("Authenticated identity cannot view tenant access roles.")
    result = await session.execute(text("""SELECT r.id,r.tenant_id,r.name,r.description,r.active,
        COALESCE(array_agg(p.permission ORDER BY p.permission) FILTER (WHERE p.granted), '{}') AS permissions,
        COUNT(DISTINCT m.id) FILTER (WHERE m.deleted_at IS NULL) AS assigned_users
        FROM tenant_access_roles r
        LEFT JOIN tenant_access_role_permissions p ON p.role_id=r.id AND p.tenant_id=r.tenant_id
        LEFT JOIN tenant_memberships m ON m.access_role_id=r.id AND m.tenant_id=r.tenant_id
        WHERE r.tenant_id=:tenant_id AND r.deleted_at IS NULL
        GROUP BY r.id ORDER BY lower(r.name),r.id"""), {"tenant_id": context.tenant_id})
    return [AccessRoleResponse.model_validate(dict(row)) for row in result.mappings().all()]


@router.post("", response_model=AccessRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(payload: AccessRoleCreate, session: SessionDependency, context: TenantContextDependency) -> AccessRoleResponse:
    require_permission(context, Permission.ROLE_MANAGE)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Nome do papel é obrigatório.")
    permissions = _permissions(payload.permissions, context=context)
    try:
        result = await session.execute(text("""INSERT INTO tenant_access_roles (tenant_id,name,description)
            VALUES (:tenant_id,:name,:description)
            RETURNING id,tenant_id,name,description,active"""),
            {"tenant_id": context.tenant_id, "name": name, "description": payload.description})
        row = dict(result.mappings().one())
        await _replace_permissions(session, tenant_id=context.tenant_id, role_id=row["id"], permissions=permissions)
        await create_audit_log(session, tenant_id=context.tenant_id, actor_external_user_id=context.external_user_id,
            action="TENANT_ACCESS_ROLE_CREATED", entity_type="tenant_access_role", entity_id=row["id"],
            metadata={"name": name, "permissions": permissions})
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Já existe um papel com esse nome.") from exc
    return AccessRoleResponse(**row, permissions=permissions, assigned_users=0)


@router.put("/{role_id}", response_model=AccessRoleResponse)
async def update_role(role_id: UUID, payload: AccessRoleUpdate, session: SessionDependency, context: TenantContextDependency) -> AccessRoleResponse:
    require_permission(context, Permission.ROLE_MANAGE)
    permissions = _permissions(payload.permissions, context=context)
    try:
        result = await session.execute(text("""UPDATE tenant_access_roles
            SET name=:name,description=:description,active=:active,updated_at=now()
            WHERE id=:role_id AND tenant_id=:tenant_id AND deleted_at IS NULL
            RETURNING id,tenant_id,name,description,active"""),
            {"tenant_id": context.tenant_id, "role_id": role_id, "name": payload.name.strip(), "description": payload.description, "active": payload.active})
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Papel não encontrado.")
        await _replace_permissions(session, tenant_id=context.tenant_id, role_id=role_id, permissions=permissions)
        count_result = await session.execute(text("SELECT count(*) FROM tenant_memberships WHERE tenant_id=:tenant_id AND access_role_id=:role_id AND deleted_at IS NULL"), {"tenant_id": context.tenant_id, "role_id": role_id})
        assigned = int(count_result.scalar_one())
        await create_audit_log(session, tenant_id=context.tenant_id, actor_external_user_id=context.external_user_id,
            action="TENANT_ACCESS_ROLE_CHANGED", entity_type="tenant_access_role", entity_id=role_id,
            metadata={"name": payload.name.strip(), "active": payload.active, "permissions": permissions})
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Já existe um papel com esse nome.") from exc
    return AccessRoleResponse(**dict(row), permissions=permissions, assigned_users=assigned)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(role_id: UUID, session: SessionDependency, context: TenantContextDependency) -> None:
    require_permission(context, Permission.ROLE_MANAGE)
    assigned = await session.execute(text("""SELECT 1 FROM tenant_memberships
        WHERE tenant_id=:tenant_id AND access_role_id=:role_id AND deleted_at IS NULL LIMIT 1"""),
        {"tenant_id": context.tenant_id, "role_id": role_id})
    if assigned.first() is not None:
        raise HTTPException(status_code=409, detail="Papel possui usuários vinculados. Reatribua os acessos antes de removê-lo.")
    result = await session.execute(text("""UPDATE tenant_access_roles SET active=FALSE,deleted_at=now(),updated_at=now()
        WHERE id=:role_id AND tenant_id=:tenant_id AND deleted_at IS NULL RETURNING id"""),
        {"tenant_id": context.tenant_id, "role_id": role_id})
    if result.first() is None:
        raise HTTPException(status_code=404, detail="Papel não encontrado.")
    await create_audit_log(session, tenant_id=context.tenant_id, actor_external_user_id=context.external_user_id,
        action="TENANT_ACCESS_ROLE_REMOVED", entity_type="tenant_access_role", entity_id=role_id, metadata={})
    await session.commit()


@router.put("/memberships/{membership_id}/role", status_code=status.HTTP_204_NO_CONTENT)
async def assign_membership_role(membership_id: UUID, payload: MembershipAccessRoleUpdate, session: SessionDependency, context: TenantContextDependency) -> None:
    """Assign one customer-defined role to a non-owner membership."""
    require_permission(context, Permission.USER_ADMIN)
    role = await session.execute(text("""SELECT id FROM tenant_access_roles
        WHERE id=:role_id AND tenant_id=:tenant_id AND active=TRUE AND deleted_at IS NULL"""),
        {"role_id": payload.access_role_id, "tenant_id": context.tenant_id})
    role_row = role.mappings().one_or_none()
    if role_row is None:
        raise HTTPException(status_code=404, detail="Papel ativo não encontrado.")
    if context.role is not MembershipRole.OWNER:
        permission_result = await session.execute(text("""SELECT permission FROM tenant_access_role_permissions
            WHERE tenant_id=:tenant_id AND role_id=:role_id AND granted=TRUE"""),
            {"tenant_id": context.tenant_id, "role_id": payload.access_role_id})
        target_permissions = {Permission(item["permission"]) for item in permission_result.mappings().all()}
        actor_permissions = {
            permission for permission in (context.permissions or frozenset())
            if isinstance(permission, Permission)
        }
        if not target_permissions.issubset(actor_permissions):
            raise HTTPException(status_code=403, detail="Não é permitido atribuir um papel com permissões superiores às suas.")
    result = await session.execute(text("""UPDATE tenant_memberships
        SET access_role_id=:role_id, updated_at=now()
        WHERE id=:membership_id AND tenant_id=:tenant_id AND deleted_at IS NULL AND role <> 'OWNER'
        RETURNING id"""), {"role_id": payload.access_role_id, "membership_id": membership_id, "tenant_id": context.tenant_id})
    if result.first() is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado ou proprietário protegido.")
    # Individual overrides must not silently survive a role reassignment.
    await session.execute(text("""DELETE FROM tenant_membership_permission_overrides
        WHERE tenant_id=:tenant_id AND membership_id=:membership_id"""),
        {"tenant_id": context.tenant_id, "membership_id": membership_id})
    await create_audit_log(session, tenant_id=context.tenant_id, actor_external_user_id=context.external_user_id,
        action="TENANT_MEMBERSHIP_ACCESS_ROLE_ASSIGNED", entity_type="tenant_membership", entity_id=membership_id,
        metadata={"access_role_id": str(payload.access_role_id)})
    await session.commit()
