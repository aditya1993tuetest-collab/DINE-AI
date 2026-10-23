"""Read-only PostgreSQL capacity guard for dataset publication."""

from dataclasses import asdict, dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True, slots=True)
class CapacityReport:
    database_size_bytes: int
    database_limit_bytes: int
    reserve_bytes: int
    estimated_additional_bytes: int
    projected_size_bytes: int
    remaining_after_projection_bytes: int
    existing_dataset_version: bool
    safe_to_publish: bool

    def to_dict(self) -> dict[str, int | bool]:
        return asdict(self)


def assess_capacity(
    *,
    database_size_bytes: int,
    accepted_rows: int,
    database_limit_bytes: int,
    reserve_bytes: int,
    estimated_bytes_per_record: int,
    existing_dataset_version: bool,
) -> CapacityReport:
    """Conservatively estimate whether another immutable version fits."""

    values = {
        "database_size_bytes": database_size_bytes,
        "accepted_rows": accepted_rows,
        "database_limit_bytes": database_limit_bytes,
        "reserve_bytes": reserve_bytes,
        "estimated_bytes_per_record": estimated_bytes_per_record,
    }
    if any(value < 0 for value in values.values()):
        raise ValueError("capacity inputs must not be negative")
    estimated = 0 if existing_dataset_version else accepted_rows * estimated_bytes_per_record
    projected = database_size_bytes + estimated
    remaining = database_limit_bytes - projected
    return CapacityReport(
        database_size_bytes=database_size_bytes,
        database_limit_bytes=database_limit_bytes,
        reserve_bytes=reserve_bytes,
        estimated_additional_bytes=estimated,
        projected_size_bytes=projected,
        remaining_after_projection_bytes=remaining,
        existing_dataset_version=existing_dataset_version,
        safe_to_publish=remaining >= reserve_bytes,
    )


def check_postgres_capacity(
    engine: Engine,
    *,
    source_name: str,
    source_revision: str,
    content_hash: str,
    accepted_rows: int,
    database_limit_bytes: int,
    reserve_bytes: int,
    estimated_bytes_per_record: int,
) -> CapacityReport:
    """Read current size and dataset identity without changing the database."""

    if engine.dialect.name != "postgresql":
        raise ValueError("capacity checks require PostgreSQL")
    with engine.connect() as connection:
        current_size = connection.scalar(text("SELECT pg_database_size(current_database())"))
        existing = connection.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM dataset_versions
                    WHERE source_name = :source_name
                      AND source_revision = :source_revision
                      AND content_hash = :content_hash
                )
                """
            ),
            {
                "source_name": source_name,
                "source_revision": source_revision,
                "content_hash": content_hash,
            },
        )
    if current_size is None:
        raise RuntimeError("PostgreSQL did not report its current database size")
    return assess_capacity(
        database_size_bytes=int(current_size),
        accepted_rows=accepted_rows,
        database_limit_bytes=database_limit_bytes,
        reserve_bytes=reserve_bytes,
        estimated_bytes_per_record=estimated_bytes_per_record,
        existing_dataset_version=bool(existing),
    )
