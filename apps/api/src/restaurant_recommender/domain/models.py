"""Canonical data model with no web or persistence dependencies."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class DatasetStatus(StrEnum):
    STAGING = "staging"
    VALIDATED = "validated"
    ACTIVE = "active"
    FAILED = "failed"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class Money:
    minor_units: int
    currency_code: str
    basis: str = "for_two_people"

    def __post_init__(self) -> None:
        if self.minor_units < 0:
            raise ValueError("minor_units must be non-negative")
        if len(self.currency_code) != 3 or not self.currency_code.isalpha():
            raise ValueError("currency_code must be a three-letter code")


@dataclass(frozen=True, slots=True)
class Rating:
    value: Decimal
    scale: Decimal

    def __post_init__(self) -> None:
        if self.scale <= 0 or self.value < 0 or self.value > self.scale:
            raise ValueError("rating must be within its positive scale")


@dataclass(frozen=True, slots=True)
class CanonicalRestaurant:
    source_key: str
    name: str
    name_normalized: str
    city: str | None
    city_normalized: str | None
    locality: str | None
    locality_normalized: str | None
    address: str | None
    cuisines: tuple[str, ...]
    cost: Money | None
    rating: Rating | None
    votes: int | None
    attributes: dict[str, Any]
    source_url: str | None
    source_payload_hash: str


@dataclass(frozen=True, slots=True)
class DatasetVersion:
    id: UUID
    source_name: str
    source_revision: str
    schema_version: str
    content_hash: str
    status: DatasetStatus
    record_count: int = 0
    rejected_count: int = 0
    quality_report: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    activated_at: datetime | None = None
