"""Provider-neutral LLM ranking contracts."""

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class RankingCandidate:
    restaurant_id: str
    name: str
    locality: str | None
    city: str | None
    cuisines: tuple[str, ...]
    rating: str | None
    rating_scale: str
    cost_minor: int | None
    currency: str | None


@dataclass(frozen=True, slots=True)
class RankingRequest:
    prompt_version: str
    system_instruction: str
    user_payload: str
    candidates: tuple[RankingCandidate, ...]
    result_count: int
    repair: bool = False


@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True, slots=True)
class RankingResult:
    content: str
    model_id: str
    provider_request_id: str | None = None
    usage: TokenUsage = TokenUsage()


# Backward-readable name inside provider adapters; the domain contract is RankingResult.
ProviderResponse = RankingResult


class ProviderFailure(RuntimeError):
    def __init__(
        self,
        category: Literal["timeout", "rate_limited", "transient", "rejected", "configuration"],
        message: str,
        *,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.retryable = retryable


class RankingModel(Protocol):
    model_id: str

    async def rank(self, request: RankingRequest, *, timeout_seconds: float) -> RankingResult: ...
