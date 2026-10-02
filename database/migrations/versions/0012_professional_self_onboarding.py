"""Add tenant-controlled professional self-onboarding.

Revision ID: 0012_prof_self_onboarding
Revises: 0011_professional_access_invites
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0012_prof_self_onboarding"
down_revision: str | None = "0011_professional_access_invites"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE professional_onboarding_links (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL UNIQUE,
            public_slug VARCHAR(80) NOT NULL UNIQUE,
            token_hash CHAR(64) NOT NULL UNIQUE,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            expires_at TIMESTAMPTZ,
            created_by_external_user_id VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,
            CONSTRAINT fk_professional_onboarding_link_tenant
                FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT,
            CONSTRAINT ck_professional_onboarding_link_status
                CHECK (status IN ('ACTIVE','REVOKED'))
        );

        CREATE INDEX ix_professional_onboarding_link_slug ON professional_onboarding_links (public_slug);

        CREATE TABLE professional_onboarding_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            document_type VARCHAR(30) NOT NULL,
            version VARCHAR(40) NOT NULL,
            title VARCHAR(200) NOT NULL,
            content TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            effective_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,
            CONSTRAINT fk_professional_onboarding_document_tenant
                FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT,
            CONSTRAINT ck_professional_onboarding_document_type
                CHECK (document_type IN ('PLATFORM_TERMS','UNIT_POLICY')),
            CONSTRAINT ck_professional_onboarding_document_status
                CHECK (status IN ('ACTIVE','INACTIVE')),
            CONSTRAINT ck_professional_onboarding_document_scope
                CHECK (
                    (document_type='PLATFORM_TERMS' AND tenant_id IS NULL)
                    OR (document_type='UNIT_POLICY' AND tenant_id IS NOT NULL)
                )
        );
        CREATE UNIQUE INDEX uq_professional_onboarding_document_active
            ON professional_onboarding_documents (
                COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid),
                document_type
            )
            WHERE status='ACTIVE' AND deleted_at IS NULL;

        CREATE TABLE professional_onboarding_requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            onboarding_link_id UUID NOT NULL,
            name VARCHAR(200) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(50),
            profession VARCHAR(120),
            council_type VARCHAR(40),
            council_number VARCHAR(80),
            status VARCHAR(30) NOT NULL DEFAULT 'PENDING_APPROVAL',
            reviewed_by_external_user_id VARCHAR(255),
            reviewed_at TIMESTAMPTZ,
            professional_id UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,
            CONSTRAINT fk_professional_onboarding_request_tenant
                FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT,
            CONSTRAINT fk_professional_onboarding_request_link
                FOREIGN KEY (onboarding_link_id) REFERENCES professional_onboarding_links (id) ON DELETE RESTRICT,
            CONSTRAINT fk_professional_onboarding_request_professional
                FOREIGN KEY (professional_id, tenant_id)
                REFERENCES professionals (id, tenant_id) ON DELETE RESTRICT,
            CONSTRAINT ck_professional_onboarding_request_status
                CHECK (status IN ('PENDING_APPROVAL','APPROVED','REJECTED')),
            CONSTRAINT ck_professional_onboarding_request_email CHECK (btrim(email) <> ''),
            CONSTRAINT ck_professional_onboarding_request_name CHECK (btrim(name) <> '')
        );
        CREATE INDEX ix_professional_onboarding_request_tenant_status
            ON professional_onboarding_requests (tenant_id, status, created_at);

        CREATE TABLE professional_onboarding_acceptances (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id UUID NOT NULL,
            document_id UUID NOT NULL,
            document_version VARCHAR(40) NOT NULL,
            accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT fk_professional_onboarding_acceptance_request
                FOREIGN KEY (request_id) REFERENCES professional_onboarding_requests (id) ON DELETE RESTRICT,
            CONSTRAINT fk_professional_onboarding_acceptance_document
                FOREIGN KEY (document_id) REFERENCES professional_onboarding_documents (id) ON DELETE RESTRICT,
            CONSTRAINT uq_professional_onboarding_acceptance UNIQUE (request_id, document_id)
        );
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS professional_onboarding_acceptances;
        DROP TABLE IF EXISTS professional_onboarding_requests;
        DROP TABLE IF EXISTS professional_onboarding_documents;
        DROP TABLE IF EXISTS professional_onboarding_links;
    """)
