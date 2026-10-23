import os
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from restaurant_recommender.domain.recommendations import RecommendationQuery
from restaurant_recommender.ingestion.adapters import FixtureAdapter
from restaurant_recommender.ingestion.quality import QualityGates
from restaurant_recommender.ingestion.service import IngestionService
from restaurant_recommender.persistence.database import transaction
from restaurant_recommender.persistence.repository import DatasetRepository, RestaurantRepository

pytestmark = pytest.mark.integration
DATABASE_URL = os.getenv("TEST_DATABASE_URL")
FIXTURE = Path(__file__).parents[3] / "docs" / "fixtures" / "restaurants_phase0.csv"


@pytest.fixture(scope="module")
def engine() -> Generator[Engine]:
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    root = Path(__file__).parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = DATABASE_URL
    command.upgrade(config, "head")
    db = create_engine(DATABASE_URL)
    yield db
    db.dispose()
    command.downgrade(config, "base")
    if old is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = old


def test_publish_idempotence_constraints_and_rollback(
    engine: Engine,
) -> None:
    gates = QualityGates(max_rejection_rate=1, max_duplicate_rate=1)
    service = IngestionService(engine, gates)
    first = service.run(FixtureAdapter(FIXTURE, revision="integration-1"))
    assert first.status == "active"
    repeated = service.run(FixtureAdapter(FIXTURE, revision="integration-1"))
    assert repeated.idempotent
    with transaction(engine) as session:
        assert len(RestaurantRepository(session).active()) == 7
        filtered = RestaurantRepository(session).filter_candidates(
            RecommendationQuery(
                city="bangalore",
                locality="indiranagar",
                cuisines=("italian",),
                budget=None,
                minimum_rating=None,
                additional_preferences=None,
                result_count=5,
            ),
            limit=500,
        )
        assert filtered
        assert all(item.locality_normalized == "indiranagar" for item in filtered)
        assert all("italian" in item.cuisines_normalized for item in filtered)

    failed = IngestionService(engine, QualityGates(min_accepted_rows=100)).run(
        FixtureAdapter(FIXTURE, revision="integration-failed")
    )
    assert failed.status == "failed"
    with transaction(engine) as session:
        versions = DatasetRepository(session).list_versions()
        active = next(version for version in versions if version.status == "active")
        assert str(active.id) == first.version_id

    second = service.run(FixtureAdapter(FIXTURE, revision="integration-2"))
    assert second.status == "active"
    with transaction(engine) as session:
        DatasetRepository(session).activate(uuid.UUID(first.version_id or ""))
    with transaction(engine) as session:
        active = next(v for v in DatasetRepository(session).list_versions() if v.status == "active")
        assert str(active.id) == first.version_id

    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            text("UPDATE restaurants SET rating = 9 WHERE dataset_version_id = :id"),
            {"id": first.version_id},
        )
