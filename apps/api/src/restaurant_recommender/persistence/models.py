"""SQLAlchemy storage model for immutable dataset versions."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


json_type = JSON().with_variant(JSONB(), "postgresql")
uuid_type = Uuid(as_uuid=True)


class DatasetVersionRow(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint(
            "source_name", "source_revision", "content_hash", name="uq_dataset_identity"
        ),
        CheckConstraint(
            "status IN ('staging','validated','active','failed','retired')",
            name="ck_dataset_status",
        ),
        CheckConstraint("record_count >= 0 AND rejected_count >= 0", name="ck_dataset_counts"),
        Index(
            "uq_one_active_dataset",
            "status",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(uuid_type, primary_key=True, default=uuid.uuid4)
    source_name: Mapped[str] = mapped_column(String(255))
    source_revision: Mapped[str] = mapped_column(String(255))
    source_split: Mapped[str] = mapped_column(String(100))
    source_schema: Mapped[dict[str, Any]] = mapped_column(json_type)
    schema_version: Mapped[str] = mapped_column(String(50), default="1")
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), index=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_report: Mapped[dict[str, Any]] = mapped_column(json_type, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    restaurants: Mapped[list["RestaurantRow"]] = relationship(cascade="all, delete-orphan")


class RestaurantRow(Base):
    __tablename__ = "restaurants"
    __table_args__ = (
        UniqueConstraint("dataset_version_id", "source_key", name="uq_restaurant_version_source"),
        CheckConstraint(
            "average_cost_minor IS NULL OR average_cost_minor >= 0", name="ck_cost_nonnegative"
        ),
        CheckConstraint("votes IS NULL OR votes >= 0", name="ck_votes_nonnegative"),
        CheckConstraint("rating_scale > 0", name="ck_rating_scale_positive"),
        CheckConstraint(
            "rating IS NULL OR (rating >= 0 AND rating <= rating_scale)", name="ck_rating_range"
        ),
        CheckConstraint(
            "currency_code IS NULL OR length(currency_code) = 3", name="ck_currency_length"
        ),
        Index("ix_restaurant_version_city", "dataset_version_id", "city_normalized"),
        Index("ix_restaurant_version_rating", "dataset_version_id", "rating"),
        Index(
            "ix_restaurant_version_cost",
            "dataset_version_id",
            "currency_code",
            "average_cost_minor",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(uuid_type, primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        uuid_type, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False
    )
    source_key: Mapped[str] = mapped_column(String(1024))
    name: Mapped[str] = mapped_column(String(255))
    name_normalized: Mapped[str] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(255))
    city_normalized: Mapped[str | None] = mapped_column(String(255))
    locality: Mapped[str | None] = mapped_column(String(255))
    locality_normalized: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(1024))
    average_cost_minor: Mapped[int | None] = mapped_column(Integer)
    currency_code: Mapped[str | None] = mapped_column(String(3))
    cost_basis: Mapped[str | None] = mapped_column(String(50))
    rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    rating_scale: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("5"))
    votes: Mapped[int | None] = mapped_column(Integer)
    attributes: Mapped[dict[str, Any]] = mapped_column(json_type, default=dict)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    source_payload_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cuisines: Mapped[list["RestaurantCuisineRow"]] = relationship(cascade="all, delete-orphan")


class RestaurantCuisineRow(Base):
    __tablename__ = "restaurant_cuisines"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "cuisine_normalized", name="uq_restaurant_cuisine"),
        Index("ix_cuisine_normalized", "cuisine_normalized"),
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        uuid_type, ForeignKey("restaurants.id", ondelete="CASCADE"), primary_key=True
    )
    cuisine: Mapped[str] = mapped_column(String(255))
    cuisine_normalized: Mapped[str] = mapped_column(String(255), primary_key=True)


class BudgetProfileRow(Base):
    __tablename__ = "budget_profiles"
    __table_args__ = (
        CheckConstraint("minimum_minor >= 0", name="ck_budget_minimum"),
        CheckConstraint(
            "maximum_minor IS NULL OR maximum_minor >= minimum_minor", name="ck_budget_range"
        ),
    )
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    currency_code: Mapped[str] = mapped_column(String(3), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    minimum_minor: Mapped[int] = mapped_column(Integer)
    maximum_minor: Mapped[int | None] = mapped_column(Integer)


class RecommendationAuditRow(Base):
    __tablename__ = "recommendation_audits"
    __table_args__ = (
        CheckConstraint("mode IN ('llm','fallback','no_match')", name="ck_audit_mode"),
        Index("ix_audit_created_at", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(uuid_type, primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(100), unique=True)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        uuid_type, ForeignKey("dataset_versions.id"), nullable=False
    )
    scoring_version: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(100))
    model_id: Mapped[str] = mapped_column(String(255))
    provider_request_id: Mapped[str | None] = mapped_column(String(255))
    query_hash: Mapped[str] = mapped_column(String(64))
    candidate_ids: Mapped[list[str]] = mapped_column(json_type)
    returned_ids: Mapped[list[str]] = mapped_column(json_type)
    mode: Mapped[str] = mapped_column(String(20))
    duration_ms: Mapped[int] = mapped_column(Integer)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    failure_category: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
