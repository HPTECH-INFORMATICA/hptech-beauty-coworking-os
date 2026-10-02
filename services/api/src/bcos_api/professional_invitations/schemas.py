"""Schemas for email-first professional access invitations."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class ProfessionalAccessInvitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    tenant_id: UUID
    tenant_name: str
    professional_id: UUID
    professional_name: str
    email: EmailStr
    status: str
    expires_at: datetime


class ProfessionalAccessInvitationCreated(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    professional_id: UUID
    email: EmailStr
    status: str
    expires_at: datetime
