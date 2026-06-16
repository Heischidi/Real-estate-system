"""Add premium subscriptions and payments"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

_subscription_tier_enum = postgresql.ENUM(
    "free", "monthly", "yearly", "lifetime",
    name="subscription_tier_enum",
    create_type=False,
)

_payment_plan_enum = postgresql.ENUM(
    "monthly", "yearly", "lifetime",
    name="payment_plan_enum",
    create_type=False,
)

_payment_status_enum = postgresql.ENUM(
    "pending", "approved", "rejected",
    name="payment_status_enum",
    create_type=False,
)


def upgrade() -> None:
    # 1. Create Enums
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE subscription_tier_enum AS ENUM ('free', 'monthly', 'yearly', 'lifetime');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE payment_plan_enum AS ENUM ('monthly', 'yearly', 'lifetime');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE payment_status_enum AS ENUM ('pending', 'approved', 'rejected');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    # 2. Add columns to subscribers
    op.add_column("subscribers", sa.Column("subscription_tier", _subscription_tier_enum, server_default="free", nullable=False))
    op.add_column("subscribers", sa.Column("subscription_expiry", sa.DateTime(timezone=True), nullable=True))

    # 3. Create payments table
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("plan", _payment_plan_enum, nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("status", _payment_status_enum, server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_payment_telegram_id", "payments", ["telegram_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_telegram_id", table_name="payments")
    op.drop_table("payments")
    op.drop_column("subscribers", "subscription_expiry")
    op.drop_column("subscribers", "subscription_tier")
    
    op.execute("DROP TYPE IF EXISTS payment_status_enum")
    op.execute("DROP TYPE IF EXISTS payment_plan_enum")
    op.execute("DROP TYPE IF EXISTS subscription_tier_enum")
