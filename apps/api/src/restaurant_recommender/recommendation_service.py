"""Deterministic recommendation orchestration."""

from dataclasses import dataclass
from typing import Literal

from restaurant_recommender.domain.normalization import comparison_text, cuisine_list, display_text
from restaurant_recommender.domain.recommendations import (
    BudgetRange,
    RecommendationQuery,
    ScoredCandidate,
    ScoringConfig,
    rank_candidates,
)
from restaurant_recommender.persistence.repository import RestaurantRepository
from restaurant_recommender.schemas import BudgetInput, RecommendationRequest


class DatasetUnavailableError(RuntimeError):
    pass


class InvalidPreferenceError(ValueError):
    def __init__(self, message: str, *, field: str, reason: str) -> None:
        super().__init__(message)
        self.field = field
        self.reason = reason


RelaxationConstraint = Literal["locality", "budget", "rating", "cuisine"]


@dataclass(frozen=True, slots=True)
class Relaxation:
    constraint: RelaxationConstraint
    description: str
    candidate_count: int


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    dataset_version: str
    scoring_version: str
    query: RecommendationQuery
    ranked: tuple[ScoredCandidate, ...]
    relaxations: tuple[Relaxation, ...]
    budget_profile_version: int | None


class RecommendationService:
    def __init__(
        self,
        repository: RestaurantRepository,
        *,
        scoring: ScoringConfig,
        candidate_limit: int,
        result_limit: int = 10,
    ) -> None:
        self.repository = repository
        self.scoring = scoring
        self.candidate_limit = candidate_limit
        self.result_limit = result_limit

    def recommend(self, request: RecommendationRequest) -> RecommendationResult:
        active = self.repository.active_version()
        if active is None:
            raise DatasetUnavailableError("no active dataset is available")
        if request.result_count > self.result_limit:
            raise InvalidPreferenceError(
                f"result count cannot exceed {self.result_limit}",
                field="resultCount",
                reason="above_configured_maximum",
            )
        scale = self.repository.active_rating_scale()
        if request.minimum_rating is not None and (scale is None or request.minimum_rating > scale):
            raise InvalidPreferenceError(
                f"minimum rating must be within the active dataset scale of {scale}",
                field="minimumRating",
                reason="out_of_active_scale",
            )
        query, budget_version = self._normalize(request)
        candidates = self.repository.filter_candidates(query, limit=self.candidate_limit)
        ranked = tuple(rank_candidates(candidates, query, self.scoring))
        relaxations = () if ranked else tuple(self._relaxations(query))
        return RecommendationResult(
            str(active.id), self.scoring.version, query, ranked, relaxations, budget_version
        )

    def _normalize(self, request: RecommendationRequest) -> tuple[RecommendationQuery, int | None]:
        city = comparison_text(request.location.city)
        locality = comparison_text(request.location.locality)
        if city is None:
            raise InvalidPreferenceError(
                "location city is required", field="location.city", reason="required"
            )
        cuisines = tuple(item.casefold() for item in cuisine_list(",".join(request.cuisines)))
        budget, version = self._budget(request.budget)
        return (
            RecommendationQuery(
                city=city,
                locality=locality,
                cuisines=cuisines,
                budget=budget,
                minimum_rating=request.minimum_rating,
                additional_preferences=display_text(request.additional_preferences),
                result_count=request.result_count,
            ),
            version,
        )

    def _budget(self, value: BudgetInput | None) -> tuple[BudgetRange | None, int | None]:
        if value is None:
            return None, None
        currency = value.currency.upper()
        if currency != "INR":
            raise InvalidPreferenceError(
                "currency is not supported", field="budget.currency", reason="unsupported_currency"
            )
        if value.tier is not None:
            resolved = self.repository.resolve_budget(value.tier, currency)
            if resolved is None:
                raise InvalidPreferenceError(
                    "budget tier is unavailable", field="budget.tier", reason="unsupported_tier"
                )
            return resolved
        return BudgetRange(value.minimum_minor or 0, value.maximum_minor, currency), None

    def _relaxations(self, query: RecommendationQuery) -> list[Relaxation]:
        values: list[Relaxation] = []
        descriptions: dict[RelaxationConstraint, str] = {
            "locality": "Search the requested city without requiring the exact locality.",
            "budget": "Search without the requested budget range.",
            "rating": "Search without the minimum rating.",
            "cuisine": "Search without requiring the requested cuisine.",
        }
        enabled: dict[RelaxationConstraint, bool] = {
            "locality": query.locality is not None,
            "budget": query.budget is not None,
            "rating": query.minimum_rating is not None,
            "cuisine": bool(query.cuisines),
        }
        for constraint, is_enabled in enabled.items():
            if is_enabled:
                count = self.repository.count_candidates(query, relax=constraint)
                if count:
                    values.append(Relaxation(constraint, descriptions[constraint], count))
        return values


def explanation(item: ScoredCandidate, query: RecommendationQuery) -> tuple[str, list[str]]:
    candidate = item.candidate
    facts: list[str] = []
    if query.cuisines:
        matched = [value for value in candidate.cuisines if value.casefold() in query.cuisines]
        if matched:
            facts.append(f"matches the requested cuisine ({', '.join(matched)})")
    if query.budget is not None and candidate.cost_minor is not None:
        facts.append("falls within the requested budget")
    if query.minimum_rating is not None and candidate.rating is not None:
        facts.append(f"has a {candidate.rating}/{candidate.rating_scale} rating")
    if candidate.locality:
        facts.append(f"is located in {candidate.locality}")
    message = (
        (candidate.name + " " + ", ".join(facts) + ".")
        if facts
        else (candidate.name + " satisfies the structured request.")
    )
    caveats = []
    if query.additional_preferences:
        caveats.append(
            "The additional free-form preference cannot be verified from the source data."
        )
    return message, caveats
