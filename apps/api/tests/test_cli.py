import json
import sys
from pathlib import Path

import pytest

from restaurant_recommender.config import get_settings
from restaurant_recommender.ingestion.cli import main

FIXTURE = Path(__file__).parents[3] / "docs" / "fixtures" / "restaurants_phase0.csv"


def test_dry_run_cli_outputs_quality_report(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    get_settings.cache_clear()
    monkeypatch.setattr(
        sys,
        "argv",
        ["nextleap-data", "ingest", "--fixture", str(FIXTURE), "--dry-run"],
    )
    main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "validated"
    assert payload["quality_report"]["accepted_rows"] == 7
    assert payload["version_id"] is None


def test_dry_run_cli_uses_failure_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("INGESTION_MIN_ROWS", "100")
    monkeypatch.setattr(
        sys,
        "argv",
        ["nextleap-data", "ingest", "--fixture", str(FIXTURE), "--dry-run"],
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert json.loads(capsys.readouterr().out)["status"] == "failed"
    get_settings.cache_clear()


def test_hugging_face_cli_requires_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setattr(sys, "argv", ["nextleap-data", "ingest", "--dataset", "owner/name"])
    with pytest.raises(SystemExit, match="--revision is required"):
        main()
