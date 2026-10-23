import hashlib
import io
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from restaurant_recommender.ingestion import adapters
from restaurant_recommender.ingestion.adapters import (
    FixtureAdapter,
    HuggingFaceCsvAdapter,
    _read_csv,
)
from restaurant_recommender.ingestion.contracts import SourceError
from restaurant_recommender.ingestion.quality import QualityGates, process_rows

FIXTURE = Path(__file__).parents[3] / "docs" / "fixtures" / "restaurants_phase0.csv"
INVALID_FIXTURE = Path(__file__).parents[3] / "docs" / "fixtures" / "restaurants_invalid_schema.csv"


def test_fixture_adapter_is_deterministic() -> None:
    first = FixtureAdapter(FIXTURE).load()
    second = FixtureAdapter(FIXTURE).load()
    assert first.metadata == second.metadata
    assert list(first.rows) == list(second.rows)


def test_fixture_adapter_rejects_unknown_schema() -> None:
    with pytest.raises(SourceError) as error:
        FixtureAdapter(INVALID_FIXTURE).load()
    assert error.value.code == "SOURCE_SCHEMA_INVALID"


def test_csv_reader_accepts_large_free_text_fields() -> None:
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    payload = f"{lines[0]}\n{lines[1].replace('1 Main Road', 'x' * 150_000)}\n".encode()

    _, rows = _read_csv(payload, source="large-field-test")

    assert len(rows[0]["address"] or "") > 131_072


def test_quality_report_tracks_duplicates_rejections_and_warnings() -> None:
    dataset = FixtureAdapter(FIXTURE).load()
    processed = process_rows(
        dataset.rows,
        QualityGates(min_accepted_rows=1, max_rejection_rate=1, max_duplicate_rate=1),
    )
    assert processed.report.source_rows == 8
    assert processed.report.accepted_rows == 7
    assert processed.report.duplicate_rows == 1
    assert processed.report.rejected_rows == 0
    assert processed.report.rejection_reasons["CONFLICTING_DUPLICATE"] == 1
    assert processed.report.warning_reasons["INVALID_COST"] == 1
    assert processed.report.warning_reasons["INVALID_VOTES"] == 1


def test_quality_gate_failure_is_explicit() -> None:
    dataset = FixtureAdapter(FIXTURE).load()
    processed = process_rows(dataset.rows, QualityGates(min_accepted_rows=100))
    assert not processed.report.passed
    assert "ACCEPTED_ROWS_BELOW_MINIMUM" in processed.report.gate_failures


def test_hugging_face_adapter_requires_pinned_revision() -> None:
    with pytest.raises(SourceError) as error:
        HuggingFaceCsvAdapter("owner/name", "main")
    assert error.value.code == "SOURCE_REVISION_UNPINNED"


def test_hugging_face_adapter_streams_and_verifies_download(monkeypatch: MonkeyPatch) -> None:
    payload = FIXTURE.read_bytes()
    monkeypatch.setattr(adapters, "urlopen", lambda *_args, **_kwargs: io.BytesIO(payload))
    adapter = HuggingFaceCsvAdapter(
        "owner/name",
        "a" * 40,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )

    dataset = adapter.load()

    assert dataset.metadata.content_hash == hashlib.sha256(payload).hexdigest()
    assert len(list(dataset.rows)) == 8
