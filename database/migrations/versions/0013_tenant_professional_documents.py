"""Make professional onboarding documents tenant-owned.

Revision ID: 0013_tenant_prof_docs
Revises: 0012_prof_self_onboarding
"""
from collections.abc import Sequence
from alembic import op

revision: str = "0013_tenant_prof_docs"
down_revision: str | None = "0012_prof_self_onboarding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.execute("""
        UPDATE professional_onboarding_documents
        SET status='INACTIVE', updated_at=now()
        WHERE document_type='PLATFORM_TERMS' AND status='ACTIVE';

        DROP INDEX uq_professional_onboarding_document_active;
        ALTER TABLE professional_onboarding_documents
            DROP CONSTRAINT ck_professional_onboarding_document_scope;
        ALTER TABLE professional_onboarding_documents
            DROP CONSTRAINT ck_professional_onboarding_document_type;
        ALTER TABLE professional_onboarding_documents
            ADD CONSTRAINT ck_professional_onboarding_document_type
            CHECK (document_type IN ('PROFESSIONAL_TERMS','UNIT_POLICY','RESERVATION_POLICY','FINANCIAL_POLICY','OTHER'));
        ALTER TABLE professional_onboarding_documents
            ADD CONSTRAINT ck_professional_onboarding_document_scope
            CHECK (tenant_id IS NOT NULL);
        CREATE UNIQUE INDEX uq_professional_onboarding_document_active
            ON professional_onboarding_documents (tenant_id, document_type)
            WHERE status='ACTIVE' AND deleted_at IS NULL;
    """)

def downgrade() -> None:
    op.execute("""
        UPDATE professional_onboarding_documents
        SET status='INACTIVE', updated_at=now()
        WHERE document_type NOT IN ('UNIT_POLICY');
        DROP INDEX uq_professional_onboarding_document_active;
        ALTER TABLE professional_onboarding_documents DROP CONSTRAINT ck_professional_onboarding_document_scope;
        ALTER TABLE professional_onboarding_documents DROP CONSTRAINT ck_professional_onboarding_document_type;
        ALTER TABLE professional_onboarding_documents
            ADD CONSTRAINT ck_professional_onboarding_document_type
            CHECK (document_type IN ('PLATFORM_TERMS','UNIT_POLICY'));
        ALTER TABLE professional_onboarding_documents
            ADD CONSTRAINT ck_professional_onboarding_document_scope
            CHECK ((document_type='PLATFORM_TERMS' AND tenant_id IS NULL) OR (document_type='UNIT_POLICY' AND tenant_id IS NOT NULL));
        CREATE UNIQUE INDEX uq_professional_onboarding_document_active
            ON professional_onboarding_documents (
                COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid),
                document_type
            ) WHERE status='ACTIVE' AND deleted_at IS NULL;
    """)
