"""Operator CLI for ingestion and dataset-version management."""

import argparse
import json
import logging
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from restaurant_recommender.config import get_settings
from restaurant_recommender.ingestion.adapters import FixtureAdapter, HuggingFaceCsvAdapter
from restaurant_recommender.ingestion.contracts import DatasetAdapter
from restaurant_recommender.ingestion.quality import QualityGates
from restaurant_recommender.ingestion.service import IngestionService
from restaurant_recommender.persistence.database import build_engine, transaction
from restaurant_recommender.persistence.repository import DatasetRepository


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nextleap-data")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest", help="validate and publish a source")
    source = ingest.add_mutually_exclusive_group(required=True)
    source.add_argument("--fixture", type=Path)
    source.add_argument("--dataset")
    ingest.add_argument("--revision")
    ingest.add_argument("--filename", default="zomato.csv")
    ingest.add_argument("--expected-sha256")
    ingest.add_argument("--dry-run", action="store_true")
    commands.add_parser("list", help="list dataset versions")
    inspect = commands.add_parser("inspect", help="inspect a dataset version")
    inspect.add_argument("version_id", type=uuid.UUID)
    activate = commands.add_parser("activate", help="activate or roll back to a version")
    activate.add_argument("version_id", type=uuid.UUID)
    return parser


def _version_dict(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "source_name": row.source_name,
        "revision": row.source_revision,
        "content_hash": row.content_hash,
        "status": row.status,
        "record_count": row.record_count,
        "rejected_count": row.rejected_count,
        "quality_report": row.quality_report,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "activated_at": row.activated_at.isoformat() if row.activated_at else None,
    }


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(message)s")
    engine = build_engine(settings.database_url)
    if args.command == "ingest":
        if args.fixture:
            adapter: DatasetAdapter = FixtureAdapter(
                args.fixture, revision=args.revision or "local-fixture"
            )
        else:
            if not args.revision:
                raise SystemExit("--revision is required with --dataset")
            adapter = HuggingFaceCsvAdapter(
                args.dataset,
                args.revision,
                filename=args.filename,
                expected_sha256=args.expected_sha256,
            )
        gates = QualityGates(
            settings.ingestion_min_rows,
            settings.ingestion_max_rejection_rate,
            settings.ingestion_max_duplicate_rate,
            settings.ingestion_min_location_coverage,
            settings.ingestion_min_cuisine_coverage,
        )
        outcome = IngestionService(engine, gates).run(adapter, dry_run=args.dry_run)
        print(json.dumps(asdict(outcome), indent=2, default=str))
        if outcome.status == "failed":
            raise SystemExit(2)
        return
    with transaction(engine) as session:
        repository = DatasetRepository(session)
        if args.command == "list":
            payload: object = [_version_dict(row) for row in repository.list_versions()]
        elif args.command == "inspect":
            row = repository.get_version(args.version_id)
            if row is None:
                raise SystemExit("dataset version not found")
            payload = _version_dict(row)
        else:
            payload = _version_dict(repository.activate(args.version_id))
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
