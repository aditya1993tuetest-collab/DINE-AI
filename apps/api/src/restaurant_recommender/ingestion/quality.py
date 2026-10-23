"""Dataset normalization, duplicate handling, and configurable quality gates."""

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

from restaurant_recommender.domain.models import CanonicalRestaurant
from restaurant_recommender.ingestion.normalize import normalize_row


@dataclass(frozen=True, slots=True)
class QualityGates:
    min_accepted_rows: int = 1
    max_rejection_rate: float = 0.10
    max_duplicate_rate: float = 0.20
    min_location_coverage: float = 0.90
    min_cuisine_coverage: float = 0.90


@dataclass(frozen=True, slots=True)
class QualityReport:
    source_rows: int
    accepted_rows: int
    rejected_rows: int
    duplicate_rows: int
    conflicting_duplicates: int
    location_coverage: float
    cuisine_coverage: float
    rating_coverage: float
    cost_coverage: float
    rejection_reasons: dict[str, int]
    warning_reasons: dict[str, int]
    gate_failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.gate_failures

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProcessedDataset:
    restaurants: tuple[CanonicalRestaurant, ...]
    report: QualityReport


def process_rows(
    rows: Iterable[Mapping[str, str | None]], gates: QualityGates | None = None
) -> ProcessedDataset:
    gates = gates or QualityGates()
    accepted: dict[str, CanonicalRestaurant] = {}
    reasons: Counter[str] = Counter()
    warnings: Counter[str] = Counter()
    source_rows = rejected = duplicates = conflicts = 0
    for row in rows:
        source_rows += 1
        result = normalize_row(row)
        warnings.update(result.warning_codes)
        if result.restaurant is None:
            rejected += 1
            reasons.update(result.rejection_codes)
            continue
        existing = accepted.get(result.restaurant.source_key)
        if existing is not None:
            duplicates += 1
            if existing.source_payload_hash != result.restaurant.source_payload_hash:
                conflicts += 1
                reasons["CONFLICTING_DUPLICATE"] += 1
            continue
        accepted[result.restaurant.source_key] = result.restaurant

    values = tuple(accepted.values())
    count = len(values)
    ratio_base = source_rows or 1
    coverage_base = count or 1
    location_coverage = sum(r.locality_normalized is not None for r in values) / coverage_base
    cuisine_coverage = sum(bool(r.cuisines) for r in values) / coverage_base
    failures: list[str] = []
    if count < gates.min_accepted_rows:
        failures.append("ACCEPTED_ROWS_BELOW_MINIMUM")
    if rejected / ratio_base > gates.max_rejection_rate:
        failures.append("REJECTION_RATE_EXCEEDED")
    if duplicates / ratio_base > gates.max_duplicate_rate:
        failures.append("DUPLICATE_RATE_EXCEEDED")
    if location_coverage < gates.min_location_coverage:
        failures.append("LOCATION_COVERAGE_BELOW_MINIMUM")
    if cuisine_coverage < gates.min_cuisine_coverage:
        failures.append("CUISINE_COVERAGE_BELOW_MINIMUM")
    return ProcessedDataset(
        values,
        QualityReport(
            source_rows,
            count,
            rejected,
            duplicates,
            conflicts,
            location_coverage,
            cuisine_coverage,
            sum(r.rating is not None for r in values) / coverage_base,
            sum(r.cost is not None for r in values) / coverage_base,
            dict(reasons),
            dict(warnings),
            tuple(failures),
        ),
    )
