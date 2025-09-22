"""Abstract base classes for Oriundi data sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Protocol, runtime_checkable

RecordBatch = List[dict]


@dataclass(slots=True)
class SourceMetadata:
    """Metadata attached to a candidate record."""

    source: str
    retrieved_at: datetime
    confidence: float


@runtime_checkable
class DataSource(Protocol):
    """Protocol representing a fetchable data source."""

    def fetch(self) -> Iterable[RecordBatch]:
        """Return an iterable of record batches."""


__all__ = ["DataSource", "SourceMetadata", "RecordBatch"]

