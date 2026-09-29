"""Extend professional profile for tenant administration.

Revision ID: 0010_admin_catalog
Revises: 0009_platform_audit
"""

from collections.abc import Sequence
from alembic import op

revision: str = "0010_admin_catalog"
down_revision: str | None = "0009_platform_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.execute("""
        ALTER TABLE professionals
            ADD COLUMN profession VARCHAR(120),
            ADD COLUMN council_type VARCHAR(40),
            ADD COLUMN council_number VARCHAR(80);

        ALTER TABLE professionals
            ADD CONSTRAINT ck_professionals_profession
                CHECK (profession IS NULL OR btrim(profession) <> ''),
            ADD CONSTRAINT ck_professionals_council_type
                CHECK (council_type IS NULL OR btrim(council_type) <> ''),
            ADD CONSTRAINT ck_professionals_council_number
                CHECK (council_number IS NULL OR btrim(council_number) <> '');
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE professionals
            DROP CONSTRAINT IF EXISTS ck_professionals_council_number,
            DROP CONSTRAINT IF EXISTS ck_professionals_council_type,
            DROP CONSTRAINT IF EXISTS ck_professionals_profession,
            DROP COLUMN IF EXISTS council_number,
            DROP COLUMN IF EXISTS council_type,
            DROP COLUMN IF EXISTS profession;
    """)
