"""Contracts shared by source adapters and the ingestion pipeline."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol


class SourceError(RuntimeError):
    """A stable, operator-safe source failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    name: str
    revision: str
    split: str
    schema: tuple[str, ...]
    content_hash: str


@dataclass(frozen=True, slots=True)
class SourceDataset:
    metadata: SourceMetadata
    rows: Iterable[Mapping[str, str | None]]


class DatasetAdapter(Protocol):
    def load(self) -> SourceDataset: ...
