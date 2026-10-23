from __future__ import annotations

import asyncio
from typing import Any

from restaurant_recommender.production import (
    Metrics,
    SharedStore,
    cached_response,
    client_identity,
    recommendation_cache_key,
)
from restaurant_recommender.schemas import RecommendationRequest, RecommendationResponse


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.count = 0
        self.closed = False

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, *, ex: int) -> None:
        assert ex > 0
        self.values[key] = value

    async def incr(self, _key: str) -> int:
        self.count += 1
        return self.count

    async def expire(self, _key: str, window: int) -> None:
        assert window > 0

    async def ttl(self, _key: str) -> int:
        return 30

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        self.closed = True


class FailingRedis:
    def __getattr__(self, _name: str) -> Any:
        async def fail(*_args: object, **_kwargs: object) -> None:
            raise ConnectionError("redis unavailable")

        return fail


def request(text: str = "Quiet dinner") -> RecommendationRequest:
    return RecommendationRequest.model_validate(
        {
            "location": {"city": "Bangalore", "locality": "Indiranagar"},
            "cuisines": ["Italian", "Indian"],
            "additionalPreferences": text,
            "resultCount": 5,
        }
    )


def test_cache_key_is_canonical_versioned_and_hides_free_text() -> None:
    first = recommendation_cache_key(
        request(),
        dataset_version="data-1",
        scoring_version="score-1",
        prompt_version="p1",
        model="m1",
    )
    equivalent = recommendation_cache_key(
        request(" quiet DINNER "),
        dataset_version="data-1",
        scoring_version="score-1",
        prompt_version="p1",
        model="m1",
    )
    changed = recommendation_cache_key(
        request(),
        dataset_version="data-2",
        scoring_version="score-1",
        prompt_version="p1",
        model="m1",
    )
    assert first == equivalent
    assert first != changed
    assert "quiet" not in first.casefold()


def test_metrics_use_only_bounded_labels() -> None:
    metrics = Metrics()
    metrics.increment("nextleap_cache_requests_total", result="hit", cache="recommendation")
    metrics.observe("nextleap_http_request_duration_seconds", 0.25, route_group="recommendation")
    output = metrics.render()
    assert 'result="hit"' in output
    assert "_sum" in output and "_count" in output


def test_disabled_store_fails_open() -> None:
    store = SharedStore("redis://invalid", enabled=False)
    assert asyncio.run(store.get_json("key")) is None
    assert asyncio.run(store.allow("key", limit=1, window=60)) == (True, 0)


def test_shared_store_cache_rate_limit_and_lifecycle() -> None:
    store = SharedStore("redis://invalid", enabled=False)
    fake = FakeRedis()
    store._client = fake
    asyncio.run(store.set_json("cache", {"value": 1}, 60))
    assert asyncio.run(store.get_json("cache")) == {"value": 1}
    assert asyncio.run(store.allow("rate", limit=1, window=60)) == (True, 30)
    assert asyncio.run(store.allow("rate", limit=1, window=60)) == (False, 30)
    assert asyncio.run(store.ping()) is True
    asyncio.run(store.close())
    assert fake.closed is True


def test_shared_store_failures_are_safe() -> None:
    store = SharedStore("redis://invalid", enabled=False)
    store._client = FailingRedis()
    assert asyncio.run(store.get_json("cache")) is None
    asyncio.run(store.set_json("cache", {"value": 1}, 60))
    assert asyncio.run(store.allow("rate", limit=1, window=60)) == (True, 0)
    assert asyncio.run(store.ping()) is False


def test_cached_response_revalidates_and_replaces_request_id() -> None:
    payload = {
        "requestId": "old",
        "datasetVersion": "data",
        "scoringVersion": "score",
        "mode": "no_match",
        "outcome": "no_match",
        "interpretedPreferences": {
            "city": "bangalore",
            "locality": None,
            "budgetRange": None,
            "cuisines": [],
            "minimumRating": None,
            "softPreferenceProvided": False,
        },
        "recommendations": [],
        "relaxations": [],
        "warnings": [],
    }
    result = cached_response(payload, "new")
    assert isinstance(result, RecommendationResponse)
    assert result.request_id == "new"
    assert client_identity("127.0.0.1") == client_identity("127.0.0.1")
    assert client_identity("127.0.0.1") != client_identity("127.0.0.2")
