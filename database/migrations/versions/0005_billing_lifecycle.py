"""Add professional billing lifecycle configuration.

Revision ID: 0005_billing_lifecycle
Revises: 0004_invoice_source_usage
Create Date: 2026-09-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_billing_lifecycle"
down_revision: str | None = "0004_invoice_source_usage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TYPE invoice_lifecycle_mode AS ENUM (
            'WEEKLY',
            'BIWEEKLY',
            'MONTHLY',
            'MANUAL'
        );
        """
    )

    op.execute(
        """
        ALTER TABLE professional_billing_contracts
            ADD COLUMN lifecycle_mode invoice_lifecycle_mode,
            ADD COLUMN lifecycle_weekday SMALLINT,
            ADD COLUMN lifecycle_biweekly_anchor DATE,
            ADD COLUMN lifecycle_month_day SMALLINT,
            ADD COLUMN lifecycle_closing_time TIME WITHOUT TIME ZONE;
        """
    )

    op.execute(
        """
        ALTER TABLE professional_billing_contracts
        ADD CONSTRAINT ck_professional_billing_contracts_lifecycle
        CHECK (
            (
                invoice_mode = 'PER_USAGE'
                AND lifecycle_mode IS NULL
                AND lifecycle_weekday IS NULL
                AND lifecycle_biweekly_anchor IS NULL
                AND lifecycle_month_day IS NULL
                AND lifecycle_closing_time IS NULL
            )
            OR
            (
                invoice_mode = 'ACCUMULATED_OPEN_INVOICE'
                AND lifecycle_mode IS NOT NULL
                AND (
                    (
                        lifecycle_mode = 'WEEKLY'
                        AND lifecycle_weekday IS NOT NULL
                        AND lifecycle_weekday BETWEEN 0 AND 6
                        AND lifecycle_biweekly_anchor IS NULL
                        AND lifecycle_month_day IS NULL
                        AND lifecycle_closing_time IS NOT NULL
                    )
                    OR
                    (
                        lifecycle_mode = 'BIWEEKLY'
                        AND lifecycle_weekday IS NULL
                        AND lifecycle_biweekly_anchor IS NOT NULL
                        AND lifecycle_month_day IS NULL
                        AND lifecycle_closing_time IS NOT NULL
                    )
                    OR
                    (
                        lifecycle_mode = 'MONTHLY'
                        AND lifecycle_weekday IS NULL
                        AND lifecycle_biweekly_anchor IS NULL
                        AND lifecycle_month_day IS NOT NULL
                        AND lifecycle_month_day BETWEEN 1 AND 31
                        AND lifecycle_closing_time IS NOT NULL
                    )
                    OR
                    (
                        lifecycle_mode = 'MANUAL'
                        AND lifecycle_weekday IS NULL
                        AND lifecycle_biweekly_anchor IS NULL
                        AND lifecycle_month_day IS NULL
                        AND lifecycle_closing_time IS NULL
                    )
                )
            )
        )
        NOT VALID;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE professional_billing_contracts
        DROP CONSTRAINT ck_professional_billing_contracts_lifecycle;
        """
    )

    op.execute(
        """
        ALTER TABLE professional_billing_contracts
            DROP COLUMN lifecycle_closing_time,
            DROP COLUMN lifecycle_month_day,
            DROP COLUMN lifecycle_biweekly_anchor,
            DROP COLUMN lifecycle_weekday,
            DROP COLUMN lifecycle_mode;
        """
    )

    op.execute(
        """
        DROP TYPE invoice_lifecycle_mode;
        """
    )
