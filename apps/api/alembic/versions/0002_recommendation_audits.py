"""Add privacy-safe recommendation audit metadata.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recommendation_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(100), nullable=False, unique=True),
        sa.Column(
            "dataset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_versions.id"),
            nullable=False,
        ),
        sa.Column("scoring_version", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("provider_request_id", sa.String(255)),
        sa.Column("query_hash", sa.String(64), nullable=False),
        sa.Column("candidate_ids", postgresql.JSONB, nullable=False),
        sa.Column("returned_ids", postgresql.JSONB, nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failure_category", sa.String(100)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("mode IN ('llm','fallback','no_match')", name="ck_audit_mode"),
    )
    op.create_index("ix_audit_created_at", "recommendation_audits", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_created_at", table_name="recommendation_audits")
    op.drop_table("recommendation_audits")
