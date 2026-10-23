import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from restaurant_recommender.ingestion.adapters import FixtureAdapter
from restaurant_recommender.ingestion.quality import QualityGates
from restaurant_recommender.ingestion.service import IngestionService
from restaurant_recommender.persistence.database import transaction
from restaurant_recommender.persistence.models import Base
from restaurant_recommender.persistence.repository import DatasetRepository, RestaurantRepository

FIXTURE = Path(__file__).parents[3] / "docs" / "fixtures" / "restaurants_phase0.csv"


@pytest.fixture
def engine() -> Generator[Engine]:
    value = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(value)
    yield value
    value.dispose()


def test_ingestion_is_idempotent_and_queries_active_records(
    engine: Engine,
) -> None:
    service = IngestionService(engine, QualityGates(max_duplicate_rate=1))
    first = service.run(FixtureAdapter(FIXTURE, revision="sqlite-1"))
    repeated = service.run(FixtureAdapter(FIXTURE, revision="sqlite-1"))
    assert first.status == "active"
    assert repeated.idempotent
    assert repeated.version_id == first.version_id
    with transaction(engine) as session:
        restaurants = RestaurantRepository(session).active(limit=10)
        assert len(restaurants) == 7
        assert restaurants[0].cuisines
        with pytest.raises(ValueError, match="limit"):
            RestaurantRepository(session).active(limit=0)


def test_failed_load_preserves_active_and_prior_version_can_be_reactivated(
    engine: Engine,
) -> None:
    service = IngestionService(engine, QualityGates(max_duplicate_rate=1))
    first = service.run(FixtureAdapter(FIXTURE, revision="sqlite-1"))
    failed = IngestionService(engine, QualityGates(min_accepted_rows=100)).run(
        FixtureAdapter(FIXTURE, revision="sqlite-failed")
    )
    assert failed.status == "failed"
    second = service.run(FixtureAdapter(FIXTURE, revision="sqlite-2"))
    with transaction(engine) as session:
        repository = DatasetRepository(session)
        repository.activate(uuid.UUID(first.version_id or ""))
        versions = repository.list_versions()
        assert next(v for v in versions if v.status == "active").id == uuid.UUID(
            first.version_id or ""
        )
        assert repository.get_version(uuid.UUID(second.version_id or "")) is not None


def test_repository_rejects_invalid_state_transitions(
    engine: Engine,
) -> None:
    metadata = FixtureAdapter(FIXTURE, revision="state-test").load().metadata
    with transaction(engine) as session:
        repository = DatasetRepository(session)
        version = repository.create_staging(metadata)
        with pytest.raises(ValueError, match="validated"):
            repository.activate(version.id)
        version.status = "failed"
        with pytest.raises(ValueError, match="staging"):
            repository.load_restaurants(version, ())
        with pytest.raises(ValueError, match="staging"):
            repository.validate(version, {"accepted_rows": 0, "rejected_rows": 0})
