"""Initial database migration — creates all tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------------------
    # ENUM types — created with IF NOT EXISTS to be idempotent on re-runs
    # ---------------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE property_type_enum AS ENUM (
                'apartment', 'flat', 'duplex', 'detached_house',
                'terrace', 'land', 'commercial'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE city_enum AS ENUM (
                'abuja', 'lagos', 'port_harcourt', 'kano'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    # ---------------------------------------------------------------------------
    # listings
    # ---------------------------------------------------------------------------
    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_listing_id", sa.String(255), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("price", sa.BigInteger, nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="NGN"),
        sa.Column(
            "property_type",
            sa.Enum(
                "apartment",
                "flat",
                "duplex",
                "detached_house",
                "terrace",
                "land",
                "commercial",
                name="property_type_enum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("bedrooms", sa.Integer, nullable=True),
        sa.Column("bathrooms", sa.Integer, nullable=True),
        sa.Column("toilets", sa.Integer, nullable=True),
        sa.Column("location", sa.Text, nullable=True),
        sa.Column(
            "city",
            sa.Enum(
                "abuja",
                "lagos",
                "port_harcourt",
                "kano",
                name="city_enum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("agent_name", sa.Text, nullable=True),
        sa.Column("agent_phone", sa.String(50), nullable=True),
        sa.Column("listing_url", sa.Text, nullable=False),
        sa.Column("image_url", sa.Text, nullable=True),
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
        sa.UniqueConstraint("source", "source_listing_id", name="uq_listing_source"),
    )
    op.create_index("ix_listing_source", "listings", ["source"])
    op.create_index("ix_listing_city", "listings", ["city"])
    op.create_index("ix_listing_property_type", "listings", ["property_type"])
    op.create_index("ix_listing_price", "listings", ["price"])
    op.create_index("ix_listing_created_at", "listings", ["created_at"])

    # ---------------------------------------------------------------------------
    # subscribers
    # ---------------------------------------------------------------------------
    op.create_table(
        "subscribers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("username", sa.String(100), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column(
            "city",
            sa.Enum(
                "abuja",
                "lagos",
                "port_harcourt",
                "kano",
                name="city_enum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("min_price", sa.BigInteger, nullable=True),
        sa.Column("max_price", sa.BigInteger, nullable=True),
        sa.Column(
            "property_type",
            sa.Enum(
                "apartment",
                "flat",
                "duplex",
                "detached_house",
                "terrace",
                "land",
                "commercial",
                name="property_type_enum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_subscriber_telegram_id", "subscribers", ["telegram_id"])

    # ---------------------------------------------------------------------------
    # notifications
    # ---------------------------------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "subscriber_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subscribers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_notification_subscriber_listing",
        "notifications",
        ["subscriber_id", "listing_id"],
    )
    op.create_index("ix_notification_sent_at", "notifications", ["sent_at"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("subscribers")
    op.drop_table("listings")

    op.execute("DROP TYPE IF EXISTS property_type_enum")
    op.execute("DROP TYPE IF EXISTS city_enum")
