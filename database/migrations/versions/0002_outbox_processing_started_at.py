"""Add processing_started_at to transactional Outbox.

Revision ID: 0002_outbox_processing_started_at
Revises: 0001_initial_bcos_schema
Create Date: 2026-09-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_outbox_processing_started_at"
down_revision: str | None = "0001_initial_bcos_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE outbox_events
        ADD COLUMN processing_started_at TIMESTAMPTZ;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE outbox_events
        DROP COLUMN processing_started_at;
        """
    )
