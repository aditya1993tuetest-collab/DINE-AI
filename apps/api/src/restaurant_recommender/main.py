"""FastAPI application and thin Phase 2 route handlers."""

import logging
import time
import uuid
from collections.abc import Iterator
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from restaurant_recommender import __version__
from restaurant_recommender.config import Settings, get_settings
from restaurant_recommender.domain.ranking import RankingModel
from restaurant_recommender.domain.recommendations import ScoringConfig
from restaurant_recommender.llm.orchestrator import (
    CircuitBreaker,
    LlmOrchestrator,
    audit_values,
)
from restaurant_recommender.llm.providers import FakeRankingModel, GroqRankingModel
from restaurant_recommender.persistence.database import build_engine
from restaurant_recommender.persistence.repository import RestaurantRepository
from restaurant_recommender.production import (
    Metrics,
    SharedStore,
    cached_response,
    client_identity,
    log_event,
    recommendation_cache_key,
)
from restaurant_recommender.recommendation_service import (
    DatasetUnavailableError,
    InvalidPreferenceError,
    RecommendationService,
    explanation,
)
from restaurant_recommender.schemas import (
    BudgetMetadataResponse,
    BudgetProfileResponse,
    BudgetRangeResponse,
    ErrorBody,
    ErrorDetail,
    ErrorEnvelope,
    InterpretedPreferences,
    LiveHealth,
    MetadataValues,
    ReadyHealth,
    RecommendationItem,
    RecommendationRequest,
    RecommendationResponse,
    RelaxationResponse,
    RestaurantResponse,
)
from restaurant_recommender.telemetry import configure_telemetry

LOGGER = logging.getLogger("nextleap.api")


def create_app(settings: Settings | None = None, *, engine: Engine | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    database = engine or build_engine(
        active_settings.database_url,
        pool_size=active_settings.database_pool_size,
        max_overflow=active_settings.database_max_overflow,
        pool_timeout=active_settings.database_pool_timeout_seconds,
        connect_timeout=active_settings.database_connect_timeout_seconds,
    )
    session_factory = sessionmaker(database, expire_on_commit=False)
    ranking_model = _ranking_model(active_settings)
    llm = LlmOrchestrator(
        ranking_model,
        prompt_version=active_settings.active_prompt_version,
        candidate_limit=active_settings.max_llm_candidates,
        prompt_character_limit=active_settings.max_prompt_characters,
        timeout_seconds=active_settings.llm_timeout_seconds,
        circuit=CircuitBreaker(
            active_settings.llm_circuit_failure_threshold,
            active_settings.llm_circuit_cooldown_seconds,
        ),
    )
    application = FastAPI(
        title="Restaurant Recommendation API",
        summary="Grounded deterministic restaurant recommendation service",
        version=__version__,
    )
    application.state.database_engine = database
    store = SharedStore(active_settings.redis_url, enabled=active_settings.app_env != "test")
    metrics = Metrics()
    application.state.shared_store = store
    application.state.metrics = metrics
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=active_settings.trusted_host_list,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.web_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    configure_telemetry(application, database, active_settings)

    @application.middleware("http")
    async def request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        existing = getattr(request.state, "request_id", "")
        supplied = request.headers.get("X-Request-ID", "")
        value = existing or (supplied if _valid_request_id(supplied) else str(uuid.uuid4()))
        request.state.request_id = value
        response = await call_next(request)
        response.headers["X-Request-ID"] = value
        return response

    @application.middleware("http")
    async def production_controls(request: Request, call_next):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        path = request.url.path
        supplied = request.headers.get("X-Request-ID", "")
        request_id_value = supplied if _valid_request_id(supplied) else str(uuid.uuid4())
        request.state.request_id = request_id_value
        content_length = request.headers.get("content-length")
        if (
            content_length
            and content_length.isdigit()
            and int(content_length) > active_settings.max_request_body_bytes
        ):
            response = _error(
                request,
                413,
                "REQUEST_TOO_LARGE",
                "The request body is too large.",
                [],
            )
            return _finalize_response(
                response,
                metrics,
                started=started,
                request_id=request_id_value,
                route_group="recommendation",
            )
        group = "recommendation" if path == "/api/v1/recommendations" else "metadata"
        if path.startswith("/api/v1/"):
            limit = (
                active_settings.recommendation_rate_limit
                if group == "recommendation"
                else active_settings.metadata_rate_limit
            )
            identity = client_identity(_client_host(request, active_settings))
            allowed, retry_after = await store.allow(
                f"nextleap:rate:{group}:{identity}",
                limit=limit,
                window=active_settings.rate_limit_window_seconds,
            )
            if not allowed:
                metrics.increment("nextleap_rate_limit_rejections_total", route_group=group)
                response = _error(
                    request,
                    429,
                    "RATE_LIMITED",
                    "Too many requests. Wait before trying again.",
                    [],
                )
                response.headers["Retry-After"] = str(retry_after)
                return _finalize_response(
                    response,
                    metrics,
                    started=started,
                    request_id=request_id_value,
                    route_group=group,
                )
        response = await call_next(request)
        route_group = group if path.startswith("/api/v1/") else "system"
        return _finalize_response(
            response,
            metrics,
            started=started,
            request_id=request_id_value,
            route_group=route_group,
        )

    @application.on_event("shutdown")
    async def shutdown() -> None:
        await store.close()
        database.dispose()

    def session() -> Iterator[Session]:
        with session_factory() as value:
            yield value

    def repository(value: Annotated[Session, Depends(session)]) -> RestaurantRepository:
        return RestaurantRepository(value)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            ErrorDetail(
                field=".".join(str(value) for value in item["loc"][1:]), reason=item["type"]
            )
            for item in exc.errors()
        ]
        return _error(request, 422, "INVALID_PREFERENCE", "The request is invalid.", details)

    @application.exception_handler(InvalidPreferenceError)
    async def preference_error(request: Request, exc: InvalidPreferenceError) -> JSONResponse:
        return _error(
            request,
            422,
            "INVALID_PREFERENCE",
            str(exc),
            [ErrorDetail(field=exc.field, reason=exc.reason)],
        )

    @application.exception_handler(DatasetUnavailableError)
    async def dataset_error(request: Request, exc: DatasetUnavailableError) -> JSONResponse:
        return _error(request, 503, "DATASET_UNAVAILABLE", str(exc), [])

    @application.exception_handler(SQLAlchemyError)
    async def repository_error(request: Request, _exc: SQLAlchemyError) -> JSONResponse:
        return _error(
            request,
            503,
            "DATASET_UNAVAILABLE",
            "The restaurant dataset is temporarily unavailable.",
            [],
        )

    @application.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        LOGGER.exception(
            "unhandled_request_error",
            extra={"request_id": getattr(request.state, "request_id", "unknown")},
            exc_info=exc,
        )
        return _error(request, 500, "INTERNAL_ERROR", "An internal error occurred.", [])

    @application.get("/health/live", tags=["health"], response_model=LiveHealth)
    async def live() -> LiveHealth:
        return LiveHealth(version=__version__)

    @application.get("/health/ready", tags=["health"], response_model=ReadyHealth)
    async def ready(
        response: Response,
        repo: Annotated[RestaurantRepository, Depends(repository)],
    ) -> ReadyHealth:
        try:
            repo.session.execute(text("SELECT 1"))
            active = repo.active_version() is not None
            redis_state: Literal["available", "unavailable", "not_required"] = "not_required"
            if active_settings.redis_required:
                redis_state = "available" if await store.ping() else "unavailable"
            is_ready = active and redis_state != "unavailable"
            if not is_ready:
                response.status_code = 503
            return ReadyHealth(
                status="ready" if is_ready else "not_ready",
                database="available",
                redis=redis_state,
                active_dataset=active,
                llm=(
                    "configured"
                    if active_settings.llm_provider != "fake" and active_settings.llm_api_key
                    else "degraded"
                ),
            )
        except SQLAlchemyError:
            response.status_code = 503
            return ReadyHealth(
                status="not_ready",
                database="unavailable",
                redis="unavailable" if active_settings.redis_required else "not_required",
                active_dataset=False,
            )

    @application.get("/metrics", include_in_schema=False)
    async def metric_values() -> PlainTextResponse:
        return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")

    @application.post(
        "/api/v1/recommendations",
        tags=["recommendations"],
        response_model=RecommendationResponse,
        responses={422: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}},
    )
    async def recommendations(
        request: Request,
        body: RecommendationRequest,
        repo: Annotated[RestaurantRepository, Depends(repository)],
    ) -> RecommendationResponse:
        scoring = ScoringConfig(version=active_settings.scoring_config_version)
        active_version = repo.active_version()
        if active_version is None:
            raise DatasetUnavailableError("no active dataset is available")
        cache_key = recommendation_cache_key(
            body,
            dataset_version=str(active_version.id),
            scoring_version=scoring.version,
            prompt_version=active_settings.active_prompt_version,
            model=active_settings.llm_model,
        )
        cached = await store.get_json(cache_key)
        if cached is not None:
            metrics.increment("nextleap_cache_requests_total", result="hit", cache="recommendation")
            metrics.increment(
                "nextleap_provider_calls_avoided_total",
                model=active_settings.llm_model,
            )
            return cached_response(cached, request.state.request_id)
        metrics.increment("nextleap_cache_requests_total", result="miss", cache="recommendation")
        result = RecommendationService(
            repo,
            scoring=scoring,
            candidate_limit=active_settings.max_filtered_records,
            result_limit=active_settings.max_results,
        ).recommend(body)
        llm_outcome = await llm.rank(result)
        metrics.increment(
            "nextleap_provider_outcomes_total",
            model=active_settings.llm_model,
            mode=llm_outcome.mode,
        )
        try:
            repo.record_audit(**audit_values(request.state.request_id, result, llm_outcome))
        except SQLAlchemyError:
            repo.session.rollback()
        interpreted = InterpretedPreferences(
            city=result.query.city,
            locality=result.query.locality,
            budget_range=(
                BudgetRangeResponse(
                    minimum_minor=result.query.budget.minimum_minor,
                    maximum_minor=result.query.budget.maximum_minor,
                    currency=result.query.budget.currency_code,
                    tier=result.query.budget.tier,
                )
                if result.query.budget
                else None
            ),
            cuisines=list(result.query.cuisines),
            minimum_rating=result.query.minimum_rating,
            soft_preference_provided=result.query.additional_preferences is not None,
        )
        items: list[RecommendationItem] = []
        for rank, scored in enumerate(llm_outcome.ranked, 1):
            candidate = scored.candidate
            generated = llm_outcome.generated.get(str(candidate.id))
            if generated:
                message, caveats = generated.explanation, list(generated.caveats)
            else:
                message, caveats = explanation(scored, result.query)
            items.append(
                RecommendationItem(
                    rank=rank,
                    restaurant=RestaurantResponse(
                        id=str(candidate.id),
                        name=candidate.name,
                        city=candidate.city,
                        locality=candidate.locality,
                        cuisines=list(candidate.cuisines),
                        rating=candidate.rating,
                        rating_scale=candidate.rating_scale,
                        estimated_cost_minor=candidate.cost_minor,
                        currency=candidate.currency_code,
                        source_url=candidate.source_url,
                    ),
                    explanation=message,
                    caveats=caveats,
                )
            )
        response = RecommendationResponse(
            request_id=request.state.request_id,
            dataset_version=result.dataset_version,
            scoring_version=result.scoring_version,
            mode=llm_outcome.mode,
            outcome="matches" if items else "no_match",
            interpreted_preferences=interpreted,
            recommendations=items,
            relaxations=[
                RelaxationResponse(
                    constraint=item.constraint,
                    description=item.description,
                    candidate_count=item.candidate_count,
                )
                for item in result.relaxations
            ],
            warnings=([llm_outcome.warning] if llm_outcome.warning else []),
        )
        await store.set_json(
            cache_key,
            response.model_dump(mode="json", by_alias=True),
            active_settings.cache_recommendation_ttl_seconds,
        )
        metrics.increment(
            "nextleap_recommendation_outcomes_total",
            mode=response.mode,
            outcome=response.outcome,
        )
        return response

    @application.get("/api/v1/metadata/locations", tags=["metadata"], response_model=MetadataValues)
    async def locations(
        request: Request,
        repo: Annotated[RestaurantRepository, Depends(repository)],
        query: Annotated[str | None, Query(max_length=100)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> MetadataValues:
        _require_dataset(repo)
        active = repo.active_version()
        assert active is not None
        key = _metadata_key("locations", str(active.id), query or "", limit)
        cached = await store.get_json(key)
        if cached is not None:
            metrics.increment("nextleap_cache_requests_total", result="hit", cache="metadata")
            cached["requestId"] = request.state.request_id
            return MetadataValues.model_validate(cached)
        metrics.increment("nextleap_cache_requests_total", result="miss", cache="metadata")
        response = MetadataValues(
            request_id=request.state.request_id, values=repo.locations(query, limit=limit)
        )
        await store.set_json(
            key,
            response.model_dump(mode="json", by_alias=True),
            active_settings.cache_metadata_ttl_seconds,
        )
        return response

    @application.get("/api/v1/metadata/cuisines", tags=["metadata"], response_model=MetadataValues)
    async def cuisines(
        request: Request,
        repo: Annotated[RestaurantRepository, Depends(repository)],
        query: Annotated[str | None, Query(max_length=100)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> MetadataValues:
        _require_dataset(repo)
        active = repo.active_version()
        assert active is not None
        key = _metadata_key("cuisines", str(active.id), query or "", limit)
        cached = await store.get_json(key)
        if cached is not None:
            metrics.increment("nextleap_cache_requests_total", result="hit", cache="metadata")
            cached["requestId"] = request.state.request_id
            return MetadataValues.model_validate(cached)
        metrics.increment("nextleap_cache_requests_total", result="miss", cache="metadata")
        response = MetadataValues(
            request_id=request.state.request_id, values=repo.cuisines(query, limit=limit)
        )
        await store.set_json(
            key,
            response.model_dump(mode="json", by_alias=True),
            active_settings.cache_metadata_ttl_seconds,
        )
        return response

    @application.get(
        "/api/v1/metadata/budgets", tags=["metadata"], response_model=BudgetMetadataResponse
    )
    async def budgets(
        request: Request,
        repo: Annotated[RestaurantRepository, Depends(repository)],
        currency: Annotated[str, Query(min_length=3, max_length=3)] = "INR",
    ) -> BudgetMetadataResponse:
        _require_dataset(repo)
        if currency.upper() != "INR":
            raise InvalidPreferenceError(
                "currency is not supported", field="currency", reason="unsupported_currency"
            )
        active = repo.active_version()
        assert active is not None
        key = _metadata_key("budgets", str(active.id), currency.upper(), 3)
        cached = await store.get_json(key)
        if cached is not None:
            metrics.increment("nextleap_cache_requests_total", result="hit", cache="metadata")
            cached["requestId"] = request.state.request_id
            return BudgetMetadataResponse.model_validate(cached)
        metrics.increment("nextleap_cache_requests_total", result="miss", cache="metadata")
        response = BudgetMetadataResponse(
            request_id=request.state.request_id,
            values=[
                BudgetProfileResponse(
                    key=item.key,
                    currency=item.currency_code,
                    minimum_minor=item.minimum_minor,
                    maximum_minor=item.maximum_minor,
                    version=item.version,
                )
                for item in repo.budgets(currency.upper())
            ],
        )
        await store.set_json(
            key,
            response.model_dump(mode="json", by_alias=True),
            active_settings.cache_metadata_ttl_seconds,
        )
        return response

    return application


def _require_dataset(repository: RestaurantRepository) -> None:
    if repository.active_version() is None:
        raise DatasetUnavailableError("no active dataset is available")


def _error(
    request: Request, status: int, code: str, message: str, details: list[ErrorDetail]
) -> JSONResponse:
    envelope = ErrorEnvelope(
        request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
        error=ErrorBody(code=code, message=message, details=details),
    )
    return JSONResponse(status_code=status, content=envelope.model_dump(by_alias=True, mode="json"))


def _valid_request_id(value: str) -> bool:
    return 1 <= len(value) <= 100 and all(
        character.isalnum() or character in "-_" for character in value
    )


def _metadata_key(kind: str, dataset_version: str, query: str, limit: int) -> str:
    normalized = query.strip().casefold()
    return f"nextleap:metadata:{dataset_version}:{kind}:{normalized}:{limit}"


def _finalize_response(
    response: Response,
    metrics: Metrics,
    *,
    started: float,
    request_id: str,
    route_group: str,
) -> Response:
    elapsed = time.perf_counter() - started
    metrics.increment(
        "nextleap_http_requests_total",
        route_group=route_group,
        status=str(response.status_code),
    )
    metrics.observe("nextleap_http_request_duration_seconds", elapsed, route_group=route_group)
    response.headers.update(
        {
            "X-Request-ID": request_id,
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
        }
    )
    log_event(
        "request_completed",
        request_id=request_id,
        route_group=route_group,
        status=response.status_code,
        duration_ms=round(elapsed * 1000, 2),
        app_version=__version__,
    )
    return response


def _ranking_model(settings: Settings) -> RankingModel:
    if settings.app_env == "test":
        return FakeRankingModel()
    if settings.llm_provider.casefold() == "groq":
        if not settings.llm_api_key:
            return FakeRankingModel(mode="failure")
        return GroqRankingModel(
            settings.llm_api_key,
            settings.llm_model,
            max_output_tokens=settings.max_llm_output_tokens,
            reasoning_effort=settings.llm_reasoning_effort,
        )
    return FakeRankingModel()


def _client_host(request: Request, settings: Settings) -> str | None:
    """Use the platform-supplied client chain only when proxy trust is explicit."""

    if settings.trust_proxy_headers:
        forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else None


app = create_app()
