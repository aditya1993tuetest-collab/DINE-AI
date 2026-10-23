"""Framework-free recommendation query and scoring model."""

import math
import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class BudgetRange:
    minimum_minor: int
    maximum_minor: int | None
    currency_code: str
    tier: str | None = None

    def __post_init__(self) -> None:
        if self.minimum_minor < 0:
            raise ValueError("minimum budget cannot be negative")
        if self.maximum_minor is not None and self.maximum_minor < self.minimum_minor:
            raise ValueError("maximum budget must not be below minimum")
        if len(self.currency_code) != 3:
            raise ValueError("currency must be a three-letter code")


@dataclass(frozen=True, slots=True)
class RecommendationQuery:
    city: str
    locality: str | None
    cuisines: tuple[str, ...]
    budget: BudgetRange | None
    minimum_rating: Decimal | None
    additional_preferences: str | None
    result_count: int


@dataclass(frozen=True, slots=True)
class Candidate:
    id: uuid.UUID
    source_key: str
    name: str
    city: str | None
    city_normalized: str | None
    locality: str | None
    locality_normalized: str | None
    cuisines: tuple[str, ...]
    cuisines_normalized: tuple[str, ...]
    cost_minor: int | None
    currency_code: str | None
    rating: Decimal | None
    rating_scale: Decimal
    votes: int | None
    source_url: str | None


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    location: float
    cuisine: float
    budget: float
    rating: float
    confidence: float
    completeness: float
    total: float


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    candidate: Candidate
    score: ScoreBreakdown


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    version: str = "score-v1"
    location_weight: float = 0.25
    cuisine_weight: float = 0.25
    budget_weight: float = 0.20
    rating_weight: float = 0.20
    confidence_weight: float = 0.05
    completeness_weight: float = 0.05
    confidence_votes: int = 100
    prior_rating_normalized: float = 0.70


def score_candidate(
    candidate: Candidate, query: RecommendationQuery, config: ScoringConfig
) -> ScoreBreakdown:
    locality_requested = query.locality is not None
    location = (
        1.0 if not locality_requested or candidate.locality_normalized == query.locality else 0.0
    )
    requested = set(query.cuisines)
    available = set(candidate.cuisines_normalized)
    cuisine = len(requested & available) / len(requested) if requested else 1.0
    budget = _budget_fit(candidate.cost_minor, query.budget)
    raw_rating = (
        float(candidate.rating / candidate.rating_scale) if candidate.rating is not None else 0.0
    )
    if candidate.rating is not None and candidate.votes is not None:
        rating = (
            candidate.votes * raw_rating + config.confidence_votes * config.prior_rating_normalized
        ) / (candidate.votes + config.confidence_votes)
    else:
        rating = raw_rating
    confidence = (
        candidate.votes / (candidate.votes + config.confidence_votes)
        if candidate.votes is not None
        else raw_rating
    )
    present = (
        candidate.locality is not None,
        bool(candidate.cuisines),
        candidate.cost_minor is not None,
        candidate.rating is not None,
        candidate.votes is not None,
    )
    completeness = sum(present) / len(present)
    total = (
        config.location_weight * location
        + config.cuisine_weight * cuisine
        + config.budget_weight * budget
        + config.rating_weight * rating
        + config.confidence_weight * confidence
        + config.completeness_weight * completeness
    )
    values = (location, cuisine, budget, rating, confidence, completeness, total)
    return ScoreBreakdown(*(min(1.0, max(0.0, value)) for value in values))


def rank_candidates(
    candidates: list[Candidate], query: RecommendationQuery, config: ScoringConfig
) -> list[ScoredCandidate]:
    scored = [ScoredCandidate(item, score_candidate(item, query, config)) for item in candidates]
    return sorted(
        scored,
        key=lambda item: (
            -item.score.total,
            -(float(item.candidate.rating) if item.candidate.rating is not None else -1),
            -(item.candidate.votes or 0),
            item.candidate.name.casefold(),
            item.candidate.source_key,
        ),
    )


def _budget_fit(cost: int | None, budget: BudgetRange | None) -> float:
    if budget is None:
        return 1.0
    if cost is None:
        return 0.0
    if budget.maximum_minor is None:
        return 1.0 if cost >= budget.minimum_minor else 0.0
    if budget.minimum_minor <= cost <= budget.maximum_minor:
        midpoint = (budget.minimum_minor + budget.maximum_minor) / 2
        half_width = max((budget.maximum_minor - budget.minimum_minor) / 2, 1)
        return 1.0 - 0.5 * min(1.0, math.fabs(cost - midpoint) / half_width)
    return 0.0
