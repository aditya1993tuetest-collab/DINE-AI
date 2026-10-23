from collections.abc import Generator
from pathlib import Path
from time import perf_counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from restaurant_recommender.config import Settings
from restaurant_recommender.ingestion.adapters import FixtureAdapter
from restaurant_recommender.ingestion.quality import QualityGates
from restaurant_recommender.ingestion.service import IngestionService
from restaurant_recommender.main import create_app
from restaurant_recommender.persistence.database import transaction
from restaurant_recommender.persistence.models import Base, BudgetProfileRow

FIXTURE = Path(__file__).parents[3] / "docs" / "fixtures" / "restaurants_phase0.csv"


@pytest.fixture
def client() -> Generator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with transaction(engine) as session:
        session.add_all(
            [
                BudgetProfileRow(
                    key="low", currency_code="INR", version=1, minimum_minor=0, maximum_minor=60_000
                ),
                BudgetProfileRow(
                    key="medium",
                    currency_code="INR",
                    version=1,
                    minimum_minor=60_001,
                    maximum_minor=150_000,
                ),
                BudgetProfileRow(
                    key="high",
                    currency_code="INR",
                    version=1,
                    minimum_minor=150_001,
                    maximum_minor=None,
                ),
            ]
        )
    IngestionService(engine, QualityGates(max_duplicate_rate=1)).run(FixtureAdapter(FIXTURE))
    with TestClient(create_app(Settings(app_env="test"), engine=engine)) as value:
        yield value
    engine.dispose()


def test_valid_request_returns_only_hard_constraint_matches(client: TestClient) -> None:
    response = client.post(
        "/api/v1/recommendations",
        headers={"X-Request-ID": "contract-test-1"},
        json={
            "location": {"city": " BANGALORE ", "locality": "Indiranagar"},
            "budget": {"tier": "medium", "currency": "INR"},
            "cuisines": ["Italian", "italian"],
            "minimumRating": 4,
            "additionalPreferences": "quiet family dinner",
            "resultCount": 5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["requestId"] == "contract-test-1"
    assert body["mode"] == "llm"
    assert body["scoringVersion"] == "score-v1"
    assert body["outcome"] == "matches"
    assert len(body["recommendations"]) == 1
    restaurant = body["recommendations"][0]["restaurant"]
    assert restaurant["locality"].casefold() == "indiranagar"
    assert restaurant["estimatedCostMinor"] <= 150_000
    assert float(restaurant["rating"]) >= 4
    assert "Italian" in restaurant["cuisines"]
    assert body["recommendations"][0]["caveats"]


def test_no_match_returns_independent_relaxations_without_results(client: TestClient) -> None:
    response = client.post(
        "/api/v1/recommendations",
        json={
            "location": {"city": "Bangalore", "locality": "Indiranagar"},
            "cuisines": ["Italian"],
            "minimumRating": 4.9,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "no_match"
    assert body["recommendations"] == []
    assert any(item["constraint"] == "rating" for item in body["relaxations"])


def test_metadata_and_readiness_use_active_dataset(client: TestClient) -> None:
    assert client.get("/health/ready").json()["status"] == "ready"
    locations = client.get("/api/v1/metadata/locations?query=ind&limit=5").json()["values"]
    cuisines = client.get("/api/v1/metadata/cuisines?query=ital&limit=5").json()["values"]
    budgets = client.get("/api/v1/metadata/budgets?currency=INR").json()["values"]
    assert locations == ["Indiranagar"]
    assert "Italian" in cuisines
    assert [item["key"] for item in budgets] == ["low", "medium", "high"]


def test_invalid_request_uses_stable_error_envelope(client: TestClient) -> None:
    response = client.post(
        "/api/v1/recommendations",
        json={"location": {"city": "Bangalore"}, "minimumRating": 9, "resultCount": 99},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PREFERENCE"
    assert response.json()["requestId"]


def test_unsupported_currency_is_rejected_without_conversion(client: TestClient) -> None:
    response = client.post(
        "/api/v1/recommendations",
        json={
            "location": {"city": "Bangalore"},
            "budget": {"tier": "low", "currency": "USD"},
        },
    )
    assert response.status_code == 422
    detail = response.json()["error"]
    assert detail["code"] == "INVALID_PREFERENCE"
    assert detail["details"][0]["reason"] == "unsupported_currency"


def test_openapi_contains_all_versioned_routes(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/recommendations" in paths
    assert "/api/v1/metadata/locations" in paths
    assert "/api/v1/metadata/cuisines" in paths
    assert "/api/v1/metadata/budgets" in paths


def test_fixture_filter_baseline_completes_within_two_seconds(client: TestClient) -> None:
    started = perf_counter()
    response = client.post(
        "/api/v1/recommendations",
        json={"location": {"city": "Bangalore"}, "resultCount": 10},
    )
    elapsed = perf_counter() - started
    assert response.status_code == 200
    assert elapsed < 2
