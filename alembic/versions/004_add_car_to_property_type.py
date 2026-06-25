"""Add car to property_type_enum"""

from __future__ import annotations

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # ALTER TYPE property_type_enum ADD VALUE IF NOT EXISTS 'car'
    # We execute COMMIT first to exit the transaction block, since PostgreSQL
    # does not allow ALTER TYPE ... ADD VALUE inside a transaction block.
    op.execute("COMMIT")
    op.execute("ALTER TYPE property_type_enum ADD VALUE IF NOT EXISTS 'car'")

def downgrade() -> None:
    pass
