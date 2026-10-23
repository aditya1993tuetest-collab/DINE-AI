"""Production cache, abuse-control, metrics, and privacy-safe logging primitives."""

from __future__ import annotations

import hashlib
import importlib
import json
import logging
import time
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from restaurant_recommender.schemas import RecommendationRequest, RecommendationResponse

try:
    REDIS_MODULE: Any = importlib.import_module("redis.asyncio")
except ImportError:  # pragma: no cover - supports source-only tooling
    REDIS_MODULE = None


LOGGER = logging.getLogger("nextleap.operations")


@dataclass(slots=True)
class Metrics:
    """Small dependency-free Prometheus registry for bounded labels."""

    counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = field(
        default_factory=lambda: defaultdict(float)
    )
    sums: dict[tuple[str, tuple[tuple[str, str], ...]], float] = field(
        default_factory=lambda: defaultdict(float)
    )
    counts: dict[tuple[str, tuple[tuple[str, str], ...]], int] = field(
        default_factory=lambda: defaultdict(int)
    )

    def increment(self, name: str, **labels: str) -> None:
        self.counters[(name, tuple(sorted(labels.items())))] += 1

    def observe(self, name: str, value: float, **labels: str) -> None:
        key = (name, tuple(sorted(labels.items())))
        self.sums[key] += value
        self.counts[key] += 1

    def render(self) -> str:
        lines: list[str] = []
        for (name, labels), value in sorted(self.counters.items()):
            lines.append(f"{name}{_labels(labels)} {value:g}")
        for (name, labels), value in sorted(self.sums.items()):
            lines.append(f"{name}_sum{_labels(labels)} {value:g}")
            lines.append(f"{name}_count{_labels(labels)} {self.counts[(name, labels)]}")
        return "\n".join(lines) + "\n"


class SharedStore:
    """Redis cache/rate-limit boundary. Failures are misses/fail-open by design."""

    def __init__(self, url: str, *, enabled: bool = True) -> None:
        self._client: Any = (
            REDIS_MODULE.Redis.from_url(url, decode_responses=True)
            if enabled and REDIS_MODULE is not None
            else None
        )

    async def get_json(self, key: str) -> dict[str, Any] | None:
        if self._client is None:
            return None
        try:
            value = await self._client.get(key)
            return json.loads(value) if value else None
        except Exception as exc:  # Redis failure must never fail a recommendation.
            LOGGER.warning("cache_read_failed", extra={"failure_type": type(exc).__name__})
            return None

    async def set_json(self, key: str, value: Mapping[str, Any], ttl: int) -> None:
        if self._client is None:
            return
        try:
            await self._client.set(key, json.dumps(value, separators=(",", ":")), ex=ttl)
        except Exception as exc:
            LOGGER.warning("cache_write_failed", extra={"failure_type": type(exc).__name__})

    async def allow(self, key: str, *, limit: int, window: int) -> tuple[bool, int]:
        if self._client is None:
            return True, 0
        try:
            current = int(await self._client.incr(key))
            if current == 1:
                await self._client.expire(key, window)
            ttl = max(int(await self._client.ttl(key)), 1)
            return current <= limit, ttl
        except Exception as exc:
            LOGGER.warning("rate_limit_failed_open", extra={"failure_type": type(exc).__name__})
            return True, 0

    async def ping(self) -> bool:
        if self._client is None:
            return False
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()


def recommendation_cache_key(
    request: RecommendationRequest,
    *,
    dataset_version: str,
    scoring_version: str,
    prompt_version: str,
    model: str,
) -> str:
    payload = request.model_dump(mode="json", by_alias=True)
    free_text = str(payload.pop("additionalPreferences", "") or "").strip().casefold()
    payload["additionalPreferencesHash"] = hashlib.sha256(free_text.encode()).hexdigest()
    payload["cuisines"] = sorted(str(value).strip().casefold() for value in payload["cuisines"])
    location = payload["location"]
    location["city"] = location["city"].strip().casefold()
    if location.get("locality"):
        location["locality"] = location["locality"].strip().casefold()
    identity = {
        "dataset": dataset_version,
        "scoring": scoring_version,
        "prompt": prompt_version,
        "model": model,
        "query": payload,
        "resultCount": request.result_count,
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return f"nextleap:recommendation:{digest}"


def cached_response(payload: Mapping[str, Any], request_id: str) -> RecommendationResponse:
    value = dict(payload)
    value["requestId"] = request_id
    return RecommendationResponse.model_validate(value)


def client_identity(client_host: str | None) -> str:
    """Hash IPs before using them as Redis keys; telemetry never stores raw addresses."""

    return hashlib.sha256((client_host or "unknown").encode()).hexdigest()[:24]


def log_event(event: str, **values: str | int | float | bool | None) -> None:
    safe = {key: value for key, value in values.items() if value is not None}
    LOGGER.info(json.dumps({"event": event, "timestamp": time.time(), **safe}, sort_keys=True))


def _labels(values: tuple[tuple[str, str], ...]) -> str:
    if not values:
        return ""
    encoded = ",".join(f'{key}="{value}"' for key, value in values)
    return "{" + encoded + "}"
