"""Local and Hugging Face CSV source adapters."""

import csv
import hashlib
import io
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from restaurant_recommender.ingestion.contracts import SourceDataset, SourceError, SourceMetadata

REQUIRED_COLUMNS = frozenset(
    {
        "url",
        "address",
        "name",
        "online_order",
        "book_table",
        "rate",
        "votes",
        "location",
        "rest_type",
        "cuisines",
        "approx_cost(for two people)",
        "listed_in(type)",
        "listed_in(city)",
    }
)

MAX_CSV_FIELD_CHARACTERS = 10 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 1024 * 1024


def _configure_csv_limit() -> None:
    # The pinned source contains free-text fields larger than Python's 128 KiB
    # default. Keep a finite ceiling so malformed input still fails promptly.
    csv.field_size_limit(max(csv.field_size_limit(), MAX_CSV_FIELD_CHARACTERS))


def _validate_schema(schema: tuple[str, ...]) -> None:
    missing = sorted(REQUIRED_COLUMNS.difference(schema))
    if missing:
        raise SourceError(
            "SOURCE_SCHEMA_INVALID", f"missing required columns: {', '.join(missing)}"
        )


def _read_csv(
    payload: bytes, *, source: str
) -> tuple[tuple[str, ...], list[dict[str, str | None]]]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceError("SOURCE_DECODING_FAILED", f"{source} is not valid UTF-8") from exc
    _configure_csv_limit()
    reader = csv.DictReader(io.StringIO(text))
    schema = tuple(reader.fieldnames or ())
    _validate_schema(schema)
    return schema, list(reader)


def _stream_csv(
    path: Path, *, source: str
) -> tuple[tuple[str, ...], Iterator[dict[str, str | None]]]:
    """Validate a downloaded CSV and iterate it without retaining its huge raw fields."""

    _configure_csv_limit()
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            schema = tuple(csv.DictReader(handle).fieldnames or ())
    except UnicodeDecodeError as exc:
        path.unlink(missing_ok=True)
        raise SourceError("SOURCE_DECODING_FAILED", f"{source} is not valid UTF-8") from exc
    try:
        _validate_schema(schema)
    except SourceError:
        path.unlink(missing_ok=True)
        raise

    def rows() -> Iterator[dict[str, str | None]]:
        try:
            with path.open(encoding="utf-8-sig", newline="") as handle:
                yield from csv.DictReader(handle)
        except UnicodeDecodeError as exc:
            raise SourceError("SOURCE_DECODING_FAILED", f"{source} is not valid UTF-8") from exc
        finally:
            path.unlink(missing_ok=True)

    return schema, rows()


class FixtureAdapter:
    def __init__(
        self, path: Path, *, revision: str = "local-fixture", split: str = "train"
    ) -> None:
        self.path = path.resolve()
        self.revision = revision
        self.split = split

    def load(self) -> SourceDataset:
        if not self.path.is_file():
            raise SourceError("SOURCE_NOT_FOUND", f"fixture not found: {self.path}")
        payload = self.path.read_bytes()
        schema, rows = _read_csv(payload, source=str(self.path))
        return SourceDataset(
            SourceMetadata(
                name=f"fixture:{self.path.name}",
                revision=self.revision,
                split=self.split,
                schema=schema,
                content_hash=hashlib.sha256(payload).hexdigest(),
            ),
            rows,
        )


class HuggingFaceCsvAdapter:
    """Download a CSV at an immutable Hugging Face revision."""

    def __init__(
        self,
        dataset: str,
        revision: str,
        *,
        filename: str = "zomato.csv",
        split: str = "train",
        expected_sha256: str | None = None,
    ) -> None:
        if not revision or revision in {"main", "master"}:
            raise SourceError("SOURCE_REVISION_UNPINNED", "an immutable revision is required")
        self.dataset = dataset
        self.revision = revision
        self.filename = filename
        self.split = split
        self.expected_sha256 = expected_sha256

    def load(self) -> SourceDataset:
        url = (
            f"https://huggingface.co/datasets/{self.dataset}/resolve/"
            f"{self.revision}/{self.filename}"
        )
        descriptor, temporary_name = tempfile.mkstemp(prefix="nextleap-zomato-", suffix=".csv")
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        digest_builder = hashlib.sha256()
        try:
            with (
                urlopen(
                    Request(url, headers={"User-Agent": "nextleap-ingestion/1"}), timeout=120
                ) as response,
                temporary_path.open("wb") as target,
            ):
                while chunk := response.read(DOWNLOAD_CHUNK_BYTES):
                    digest_builder.update(chunk)
                    target.write(chunk)
        except (HTTPError, URLError, TimeoutError) as exc:
            temporary_path.unlink(missing_ok=True)
            raise SourceError(
                "SOURCE_DOWNLOAD_FAILED", f"unable to download {self.dataset}"
            ) from exc
        digest = digest_builder.hexdigest()
        if self.expected_sha256 and digest != self.expected_sha256:
            temporary_path.unlink(missing_ok=True)
            raise SourceError("SOURCE_HASH_MISMATCH", "downloaded content hash did not match")
        schema, rows = _stream_csv(temporary_path, source=self.dataset)
        return SourceDataset(
            SourceMetadata(self.dataset, self.revision, self.split, schema, digest), rows
        )
