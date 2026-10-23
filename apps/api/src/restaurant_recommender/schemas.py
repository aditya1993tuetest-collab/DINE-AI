"""Versioned HTTP transport contracts."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


def _camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(item.capitalize() for item in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True)


class LiveHealth(ApiModel):
    status: Literal["ok"] = "ok"
    service: Literal["restaurant-recommendation-api"] = "restaurant-recommendation-api"
    version: str


class ReadyHealth(ApiModel):
    status: Literal["ready", "not_ready"]
    phase: Literal[5] = 5
    database: Literal["available", "unavailable"]
    redis: Literal["available", "unavailable", "not_required"]
    active_dataset: bool
    llm: Literal["configured", "degraded"] = "degraded"


class LocationInput(ApiModel):
    city: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    locality: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
        | None
    ) = None


class BudgetInput(ApiModel):
    tier: Literal["low", "medium", "high"] | None = None
    currency: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=3, max_length=3)
    ] = "INR"
    minimum_minor: int | None = Field(default=None, ge=0)
    maximum_minor: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_choice(self) -> "BudgetInput":
        has_range = self.minimum_minor is not None or self.maximum_minor is not None
        if self.tier is not None and has_range:
            raise ValueError("provide either a budget tier or a numeric range")
        if self.tier is None and not has_range:
            raise ValueError("a budget tier or numeric range is required")
        minimum = self.minimum_minor or 0
        if self.maximum_minor is not None and self.maximum_minor < minimum:
            raise ValueError("maximumMinor must not be below minimumMinor")
        return self


class RecommendationRequest(ApiModel):
    location: LocationInput
    budget: BudgetInput | None = None
    cuisines: list[
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    ] = Field(default_factory=list, max_length=10)
    minimum_rating: Decimal | None = Field(default=None, ge=0, le=5)
    additional_preferences: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
        | None
    ) = None
    result_count: int = Field(default=5, ge=1, le=10)


class BudgetRangeResponse(ApiModel):
    minimum_minor: int
    maximum_minor: int | None
    currency: str
    tier: str | None = None


class InterpretedPreferences(ApiModel):
    city: str
    locality: str | None
    budget_range: BudgetRangeResponse | None
    cuisines: list[str]
    minimum_rating: Decimal | None
    soft_preference_provided: bool


class RestaurantResponse(ApiModel):
    id: str
    name: str
    city: str | None
    locality: str | None
    cuisines: list[str]
    rating: Decimal | None
    rating_scale: Decimal
    estimated_cost_minor: int | None
    currency: str | None
    source_url: str | None


class RecommendationItem(ApiModel):
    rank: int
    restaurant: RestaurantResponse
    explanation: str
    caveats: list[str]


class RelaxationResponse(ApiModel):
    constraint: Literal["locality", "budget", "rating", "cuisine"]
    description: str
    candidate_count: int


class RecommendationResponse(ApiModel):
    request_id: str
    dataset_version: str
    scoring_version: str
    mode: Literal["llm", "fallback", "no_match"]
    outcome: Literal["matches", "no_match"]
    interpreted_preferences: InterpretedPreferences
    recommendations: list[RecommendationItem]
    relaxations: list[RelaxationResponse]
    warnings: list[str]


class MetadataValues(ApiModel):
    request_id: str
    values: list[str]


class BudgetProfileResponse(ApiModel):
    key: str
    currency: str
    minimum_minor: int
    maximum_minor: int | None
    version: int


class BudgetMetadataResponse(ApiModel):
    request_id: str
    values: list[BudgetProfileResponse]


class ErrorDetail(ApiModel):
    field: str | None = None
    reason: str


class ErrorBody(ApiModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorEnvelope(ApiModel):
    request_id: str
    error: ErrorBody
