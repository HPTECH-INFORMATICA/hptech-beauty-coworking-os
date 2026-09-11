"""Add PER_USAGE physical Invoice identity.

Revision ID: 0004_invoice_source_usage
Revises: 0003_prof_billing_contracts
"""

from alembic import op


revision = "0004_invoice_source_usage"
down_revision = "0003_prof_billing_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE invoices
        ADD COLUMN source_usage_id UUID;
        """
    )

    op.execute(
        """
        ALTER TABLE invoices
        ADD CONSTRAINT fk_invoices_source_usage
        FOREIGN KEY (source_usage_id, tenant_id)
        REFERENCES usages (id, tenant_id)
        ON DELETE RESTRICT;
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX uq_invoices_tenant_source_usage
        ON invoices (tenant_id, source_usage_id)
        WHERE source_usage_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS uq_invoices_tenant_source_usage;
        """
    )

    op.execute(
        """
        ALTER TABLE invoices
        DROP CONSTRAINT IF EXISTS fk_invoices_source_usage;
        """
    )

    op.execute(
        """
        ALTER TABLE invoices
        DROP COLUMN IF EXISTS source_usage_id;
        """
    )
