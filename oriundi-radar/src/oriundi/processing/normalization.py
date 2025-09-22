"""Normalization helpers for candidate data."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable, List

from ..data_sources.base import RecordBatch

EXPECTED_KEYS = {
    "player.full_name",
    "player.birth_date",
    "player.birth_place",
    "player.current_club",
    "player.position",
    "article.url",
    "article.text",
}


def normalize_candidates(batches: Iterable[RecordBatch]) -> RecordBatch:
    """Normalize heterogenous batches into a canonical schema."""

    normalized: RecordBatch = []
    for batch in batches:
        for record in batch:
            normalized.append(_normalize_record(record))
    return normalized


def _normalize_record(record: dict) -> dict:
    normalized = {key: record.get(key) for key in EXPECTED_KEYS}
    normalized["player.full_name"] = _clean_name(normalized.get("player.full_name") or "")
    normalized["player.birth_date"] = _parse_date(normalized.get("player.birth_date"))
    normalized["article.url"] = (normalized.get("article.url") or "").strip()
    normalized["ingestion.batch_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    normalized.update({k: v for k, v in record.items() if k not in normalized})
    return normalized


def _clean_name(value: str) -> str:
    return " ".join(value.strip().split())


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
    return None


__all__ = ["normalize_candidates"]

