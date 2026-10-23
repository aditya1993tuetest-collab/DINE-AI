"""Bounded LLM ranking with repair, retry, circuit breaking, and fallback."""

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Literal

from restaurant_recommender.domain.ranking import ProviderFailure, RankingModel, TokenUsage
from restaurant_recommender.domain.recommendations import ScoredCandidate
from restaurant_recommender.llm.guard import GuardedRanking, OutputValidationError, validate_output
from restaurant_recommender.llm.prompt import PromptTooLargeError, build_ranking_request
from restaurant_recommender.recommendation_service import RecommendationResult


@dataclass(frozen=True, slots=True)
class GeneratedText:
    explanation: str
    caveats: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LlmRankingOutcome:
    ranked: tuple[ScoredCandidate, ...]
    generated: dict[str, GeneratedText]
    mode: Literal["llm", "fallback", "no_match"]
    warning: str | None
    prompt_version: str
    model_id: str
    provider_request_id: str | None
    usage: TokenUsage
    failure_category: str | None
    duration_ms: int
    candidate_ids: tuple[str, ...]


class CircuitBreaker:
    def __init__(self, failure_threshold: int, cooldown_seconds: float) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failures = 0
        self.opened_at: float | None = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if time.monotonic() - self.opened_at >= self.cooldown_seconds:
            self.opened_at = None
            self.failures = 0
            return True
        return False

    def success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.monotonic()


class LlmOrchestrator:
    def __init__(
        self,
        model: RankingModel,
        *,
        prompt_version: str,
        candidate_limit: int,
        prompt_character_limit: int,
        timeout_seconds: float,
        circuit: CircuitBreaker,
    ) -> None:
        self.model = model
        self.prompt_version = prompt_version
        self.candidate_limit = candidate_limit
        self.prompt_character_limit = prompt_character_limit
        self.timeout_seconds = timeout_seconds
        self.circuit = circuit

    async def rank(self, result: RecommendationResult) -> LlmRankingOutcome:
        started = time.monotonic()
        baseline = result.ranked[: result.query.result_count]
        candidates = result.ranked[: self.candidate_limit]
        candidate_ids = tuple(str(item.candidate.id) for item in candidates)
        if not candidates:
            return LlmRankingOutcome(
                (),
                {},
                "no_match",
                None,
                self.prompt_version,
                self.model.model_id,
                None,
                TokenUsage(),
                None,
                int((time.monotonic() - started) * 1000),
                (),
            )
        if not self.circuit.allow():
            return self._fallback(baseline, candidate_ids, started, "circuit_open", None)
        try:
            request = build_ranking_request(
                candidates,
                result.query,
                candidate_limit=self.candidate_limit,
                character_limit=self.prompt_character_limit,
                prompt_version=self.prompt_version,
            )
        except (PromptTooLargeError, ValueError):
            return self._fallback(baseline, candidate_ids, started, "prompt_invalid", None)

        response = None
        failure_category: str | None = None
        for attempt in range(2):
            try:
                response = await asyncio.wait_for(
                    self.model.rank(request, timeout_seconds=self.timeout_seconds),
                    timeout=self.timeout_seconds,
                )
                break
            except TimeoutError:
                failure_category = "timeout"
            except ProviderFailure as exc:
                failure_category = exc.category
                if not exc.retryable:
                    break
            if attempt == 0:
                await asyncio.sleep(0.05)
        if response is None:
            self.circuit.failure()
            return self._fallback(
                baseline, candidate_ids, started, failure_category or "provider", None
            )

        guarded: GuardedRanking | None = None
        try:
            guarded = validate_output(
                response.content,
                candidate_ids=set(candidate_ids),
                result_count=request.result_count,
            )
        except OutputValidationError:
            try:
                repair = build_ranking_request(
                    candidates,
                    result.query,
                    candidate_limit=self.candidate_limit,
                    character_limit=self.prompt_character_limit,
                    prompt_version=self.prompt_version,
                    repair=True,
                )
                repaired = await asyncio.wait_for(
                    self.model.rank(repair, timeout_seconds=self.timeout_seconds),
                    timeout=self.timeout_seconds,
                )
                guarded = validate_output(
                    repaired.content,
                    candidate_ids=set(candidate_ids),
                    result_count=repair.result_count,
                )
                response = repaired
            except (OutputValidationError, ProviderFailure, TimeoutError, PromptTooLargeError):
                self.circuit.failure()
                return self._fallback(
                    baseline, candidate_ids, started, "invalid_output", response.model_id
                )
        assert guarded is not None
        by_id = {str(item.candidate.id): item for item in candidates}
        ordered = tuple(by_id[item.restaurant_id] for item in guarded.ranked)
        generated = {
            item.restaurant_id: GeneratedText(item.explanation, tuple(item.caveats))
            for item in guarded.ranked
        }
        self.circuit.success()
        return LlmRankingOutcome(
            ordered,
            generated,
            "llm",
            None,
            self.prompt_version,
            response.model_id,
            response.provider_request_id,
            response.usage,
            None,
            int((time.monotonic() - started) * 1000),
            candidate_ids,
        )

    def _fallback(
        self,
        baseline: tuple[ScoredCandidate, ...],
        candidate_ids: tuple[str, ...],
        started: float,
        category: str,
        model_id: str | None,
    ) -> LlmRankingOutcome:
        return LlmRankingOutcome(
            baseline,
            {},
            "fallback",
            "Personalized ranking is temporarily unavailable; deterministic ranking was used.",
            self.prompt_version,
            model_id or self.model.model_id,
            None,
            TokenUsage(),
            category,
            int((time.monotonic() - started) * 1000),
            candidate_ids,
        )


def canonical_query_hash(result: RecommendationResult) -> str:
    value = asdict(result.query)
    value["additional_preferences"] = bool(result.query.additional_preferences)
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def audit_values(
    request_id: str, result: RecommendationResult, outcome: LlmRankingOutcome
) -> dict[str, object]:
    return {
        "id": uuid.uuid4(),
        "request_id": request_id,
        "dataset_version_id": uuid.UUID(result.dataset_version),
        "scoring_version": result.scoring_version,
        "prompt_version": outcome.prompt_version,
        "model_id": outcome.model_id,
        "provider_request_id": outcome.provider_request_id,
        "query_hash": canonical_query_hash(result),
        "candidate_ids": list(outcome.candidate_ids),
        "returned_ids": [str(item.candidate.id) for item in outcome.ranked],
        "mode": outcome.mode,
        "duration_ms": outcome.duration_ms,
        "input_tokens": outcome.usage.input_tokens,
        "output_tokens": outcome.usage.output_tokens,
        "failure_category": outcome.failure_category,
    }
