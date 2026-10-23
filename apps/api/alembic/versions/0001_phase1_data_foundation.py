"""Phase 1 immutable dataset foundation.

Revision ID: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dataset_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_revision", sa.String(255), nullable=False),
        sa.Column("source_split", sa.String(100), nullable=False),
        sa.Column("source_schema", postgresql.JSONB, nullable=False),
        sa.Column("schema_version", sa.String(50), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("record_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("quality_report", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('staging','validated','active','failed','retired')",
            name="ck_dataset_status",
        ),
        sa.CheckConstraint("record_count >= 0 AND rejected_count >= 0", name="ck_dataset_counts"),
        sa.UniqueConstraint(
            "source_name", "source_revision", "content_hash", name="uq_dataset_identity"
        ),
    )
    op.create_index("ix_dataset_versions_status", "dataset_versions", ["status"])
    op.create_index(
        "uq_one_active_dataset",
        "dataset_versions",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "restaurants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_key", sa.String(1024), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_normalized", sa.String(255), nullable=False),
        sa.Column("city", sa.String(255)),
        sa.Column("city_normalized", sa.String(255)),
        sa.Column("locality", sa.String(255)),
        sa.Column("locality_normalized", sa.String(255)),
        sa.Column("address", sa.String(1024)),
        sa.Column("average_cost_minor", sa.Integer),
        sa.Column("currency_code", sa.String(3)),
        sa.Column("cost_basis", sa.String(50)),
        sa.Column("rating", sa.Numeric(4, 2)),
        sa.Column("rating_scale", sa.Numeric(4, 2), nullable=False),
        sa.Column("votes", sa.Integer),
        sa.Column("attributes", postgresql.JSONB, nullable=False),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("source_payload_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "average_cost_minor IS NULL OR average_cost_minor >= 0", name="ck_cost_nonnegative"
        ),
        sa.CheckConstraint("votes IS NULL OR votes >= 0", name="ck_votes_nonnegative"),
        sa.CheckConstraint("rating_scale > 0", name="ck_rating_scale_positive"),
        sa.CheckConstraint(
            "rating IS NULL OR (rating >= 0 AND rating <= rating_scale)", name="ck_rating_range"
        ),
        sa.CheckConstraint(
            "currency_code IS NULL OR length(currency_code) = 3", name="ck_currency_length"
        ),
        sa.UniqueConstraint(
            "dataset_version_id", "source_key", name="uq_restaurant_version_source"
        ),
    )
    op.create_index(
        "ix_restaurant_version_city", "restaurants", ["dataset_version_id", "city_normalized"]
    )
    op.create_index("ix_restaurant_version_rating", "restaurants", ["dataset_version_id", "rating"])
    op.create_index(
        "ix_restaurant_version_cost",
        "restaurants",
        ["dataset_version_id", "currency_code", "average_cost_minor"],
    )
    op.create_table(
        "restaurant_cuisines",
        sa.Column(
            "restaurant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("cuisine", sa.String(255), nullable=False),
        sa.Column("cuisine_normalized", sa.String(255), primary_key=True),
    )
    op.create_index("ix_cuisine_normalized", "restaurant_cuisines", ["cuisine_normalized"])
    op.create_table(
        "budget_profiles",
        sa.Column("key", sa.String(50), primary_key=True),
        sa.Column("currency_code", sa.String(3), primary_key=True),
        sa.Column("version", sa.Integer, primary_key=True),
        sa.Column("minimum_minor", sa.Integer, nullable=False),
        sa.Column("maximum_minor", sa.Integer),
        sa.CheckConstraint("minimum_minor >= 0", name="ck_budget_minimum"),
        sa.CheckConstraint(
            "maximum_minor IS NULL OR maximum_minor >= minimum_minor", name="ck_budget_range"
        ),
    )
    op.bulk_insert(
        sa.table(
            "budget_profiles",
            sa.column("key"),
            sa.column("currency_code"),
            sa.column("version"),
            sa.column("minimum_minor"),
            sa.column("maximum_minor"),
        ),
        [
            {
                "key": "low",
                "currency_code": "INR",
                "version": 1,
                "minimum_minor": 0,
                "maximum_minor": 60000,
            },
            {
                "key": "medium",
                "currency_code": "INR",
                "version": 1,
                "minimum_minor": 60001,
                "maximum_minor": 150000,
            },
            {
                "key": "high",
                "currency_code": "INR",
                "version": 1,
                "minimum_minor": 150001,
                "maximum_minor": None,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("budget_profiles")
    op.drop_index("ix_cuisine_normalized", table_name="restaurant_cuisines")
    op.drop_table("restaurant_cuisines")
    op.drop_index("ix_restaurant_version_cost", table_name="restaurants")
    op.drop_index("ix_restaurant_version_rating", table_name="restaurants")
    op.drop_index("ix_restaurant_version_city", table_name="restaurants")
    op.drop_table("restaurants")
    op.drop_index("uq_one_active_dataset", table_name="dataset_versions")
    op.drop_index("ix_dataset_versions_status", table_name="dataset_versions")
    op.drop_table("dataset_versions")
