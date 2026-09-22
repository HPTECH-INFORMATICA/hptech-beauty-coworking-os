"""HTTP schemas for tenant membership administration."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from bcos_api.tenancy.membership import MembershipRole, MembershipStatus


class MembershipInvitationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_user_id: str = Field(min_length=1, max_length=255)
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
