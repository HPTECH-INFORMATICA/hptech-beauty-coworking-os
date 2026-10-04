"""HTTP schemas for tenant membership administration."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from bcos_api.tenancy.membership import MembershipRole, MembershipStatus
from bcos_api.tenancy.rbac import Permission


class MembershipInvitationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=3, max_length=255)
    role: MembershipRole = MembershipRole.RECEPTION
    access_role_id: UUID


class MembershipDetailsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=160)
    role: MembershipRole


class MembershipStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: MembershipStatus


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    external_user_id: str
    role: MembershipRole
    status: MembershipStatus
    display_name: str | None = None
    email: str | None = None
    access_role_id: UUID | None = None
    permissions: list[Permission] = Field(default_factory=list)


class MembershipPermissionsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    permissions: list[Permission]


class TeamInvitationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    display_name: str
    email: str
    role: MembershipRole
    status: str
    expires_at: str
