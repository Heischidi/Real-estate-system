"""Add listing_purpose to listings"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

_listing_purpose_enum = postgresql.ENUM(
    "rent", "sale",
    name="listing_purpose_enum",
    create_type=False,
)

def upgrade() -> None:
    # Create enum type safely
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE listing_purpose_enum AS ENUM ('rent', 'sale');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Add column
    op.add_column("listings", sa.Column("listing_purpose", _listing_purpose_enum, nullable=True))
    op.create_index("ix_listing_purpose", "listings", ["listing_purpose"])


def downgrade() -> None:
    op.drop_index("ix_listing_purpose", table_name="listings")
    op.drop_column("listings", "listing_purpose")
    op.execute("DROP TYPE IF EXISTS listing_purpose_enum")
