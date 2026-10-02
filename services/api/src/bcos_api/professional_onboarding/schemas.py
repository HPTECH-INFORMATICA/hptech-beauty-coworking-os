"""Contracts for professional self-onboarding."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OnboardingDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    document_type: str
    version: str
    title: str
    content: str


class PublicOnboarding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_name: str
    documents: list[OnboardingDocument]


class ProfessionalOnboardingSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    profession: str | None = Field(default=None, max_length=120)
    council_type: str | None = Field(default=None, max_length=40)
    council_number: str | None = Field(default=None, max_length=80)
    accepted_document_ids: list[UUID] = Field(min_length=2)


class ProfessionalOnboardingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    tenant_id: UUID
    tenant_name: str
    name: str
    email: EmailStr
    phone: str | None
    profession: str | None
    council_type: str | None
    council_number: str | None
    status: str
    created_at: datetime


class ProfessionalOnboardingLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    public_slug: str
    public_path: str


class OnboardingDocumentPublish(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class ManagedOnboardingDocument(OnboardingDocument):
    tenant_id: UUID | None
    status: str
    effective_at: datetime
