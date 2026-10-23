"""End-to-end staging, validation, and atomic publication service."""

import logging
import time
import uuid
from dataclasses import dataclass

from sqlalchemy.engine import Engine

from restaurant_recommender.ingestion.contracts import DatasetAdapter
from restaurant_recommender.ingestion.quality import QualityGates, process_rows
from restaurant_recommender.persistence.database import transaction
from restaurant_recommender.persistence.repository import DatasetRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IngestionOutcome:
    job_id: str
    version_id: str | None
    status: str
    idempotent: bool
    quality_report: dict[str, object]
    duration_seconds: float


class IngestionService:
    def __init__(self, engine: Engine, gates: QualityGates) -> None:
        self.engine = engine
        self.gates = gates

    def run(self, adapter: DatasetAdapter, *, dry_run: bool = False) -> IngestionOutcome:
        job_id = str(uuid.uuid4())
        started = time.monotonic()
        logger.info("ingestion_started", extra={"job_id": job_id, "dry_run": dry_run})
        dataset = adapter.load()
        processed = process_rows(dataset.rows, self.gates)
        report: dict[str, object] = processed.report.to_dict()
        if dry_run:
            return IngestionOutcome(
                job_id,
                None,
                "validated" if processed.report.passed else "failed",
                False,
                report,
                time.monotonic() - started,
            )

        with transaction(self.engine) as session:
            repository = DatasetRepository(session)
            existing = repository.find_idempotent(dataset.metadata)
            if existing is not None:
                return IngestionOutcome(
                    job_id,
                    str(existing.id),
                    existing.status,
                    True,
                    existing.quality_report,
                    time.monotonic() - started,
                )
            version = repository.create_staging(dataset.metadata)
            if not processed.report.passed:
                repository.fail(version, report)
                status = "failed"
            else:
                repository.load_restaurants(version, processed.restaurants)
                repository.validate(version, report)
                repository.activate(version.id)
                status = "active"
            version_id = str(version.id)
        duration = time.monotonic() - started
        logger.info(
            "ingestion_finished",
            extra={
                "job_id": job_id,
                "version_id": version_id,
                "status": status,
                "accepted_rows": processed.report.accepted_rows,
                "duration_seconds": duration,
            },
        )
        return IngestionOutcome(job_id, version_id, status, False, report, duration)
