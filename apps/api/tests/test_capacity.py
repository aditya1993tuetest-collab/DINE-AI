from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine import Engine

from restaurant_recommender.ingestion.capacity import assess_capacity, check_postgres_capacity


def test_capacity_reserves_space_for_a_new_immutable_version() -> None:
    report = assess_capacity(
        database_size_bytes=20_000_000,
        accepted_rows=50_000,
        database_limit_bytes=1_000_000_000,
        reserve_bytes=100_000_000,
        estimated_bytes_per_record=12_288,
        existing_dataset_version=False,
    )

    assert report.estimated_additional_bytes == 614_400_000
    assert report.projected_size_bytes == 634_400_000
    assert report.safe_to_publish is True
    assert report.to_dict()["safe_to_publish"] is True


def test_capacity_blocks_when_projection_consumes_reserve() -> None:
    report = assess_capacity(
        database_size_bytes=400_000_000,
        accepted_rows=50_000,
        database_limit_bytes=1_000_000_000,
        reserve_bytes=100_000_000,
        estimated_bytes_per_record=12_288,
        existing_dataset_version=False,
    )

    assert report.safe_to_publish is False
    assert report.remaining_after_projection_bytes < 0


def test_capacity_does_not_charge_an_idempotent_rerun_twice() -> None:
    report = assess_capacity(
        database_size_bytes=700_000_000,
        accepted_rows=50_000,
        database_limit_bytes=1_000_000_000,
        reserve_bytes=100_000_000,
        estimated_bytes_per_record=12_288,
        existing_dataset_version=True,
    )

    assert report.estimated_additional_bytes == 0
    assert report.safe_to_publish is True


def test_capacity_rejects_negative_inputs() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        assess_capacity(
            database_size_bytes=-1,
            accepted_rows=0,
            database_limit_bytes=1_000_000_000,
            reserve_bytes=100_000_000,
            estimated_bytes_per_record=12_288,
            existing_dataset_version=False,
        )


def test_postgres_capacity_reads_size_and_existing_identity() -> None:
    engine = MagicMock()
    cast(Any, engine).dialect.name = "postgresql"
    connection = cast(Any, engine).connect.return_value.__enter__.return_value
    connection.scalar.side_effect = [700_000_000, True]

    report = check_postgres_capacity(
        cast(Engine, engine),
        source_name="owner/dataset",
        source_revision="abc123",
        content_hash="f" * 64,
        accepted_rows=50_000,
        database_limit_bytes=1_000_000_000,
        reserve_bytes=100_000_000,
        estimated_bytes_per_record=12_288,
    )

    assert report.existing_dataset_version is True
    assert report.estimated_additional_bytes == 0
    assert connection.scalar.call_count == 2


def test_postgres_capacity_rejects_other_databases() -> None:
    engine = MagicMock()
    cast(Any, engine).dialect.name = "sqlite"

    with pytest.raises(ValueError, match="require PostgreSQL"):
        check_postgres_capacity(
            cast(Engine, engine),
            source_name="owner/dataset",
            source_revision="abc123",
            content_hash="f" * 64,
            accepted_rows=1,
            database_limit_bytes=1_000_000_000,
            reserve_bytes=100_000_000,
            estimated_bytes_per_record=12_288,
        )


def test_postgres_capacity_requires_a_reported_size() -> None:
    engine = MagicMock()
    cast(Any, engine).dialect.name = "postgresql"
    connection = cast(Any, engine).connect.return_value.__enter__.return_value
    connection.scalar.side_effect = [None, False]

    with pytest.raises(RuntimeError, match="did not report"):
        check_postgres_capacity(
            cast(Engine, engine),
            source_name="owner/dataset",
            source_revision="abc123",
            content_hash="f" * 64,
            accepted_rows=1,
            database_limit_bytes=1_000_000_000,
            reserve_bytes=100_000_000,
            estimated_bytes_per_record=12_288,
        )
