"""Utilities to enrich candidate data with social signals."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable, List

try:
    from tqdm import tqdm  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    def tqdm(iterable, **_kwargs):
        return iterable

from ..data_sources.base import RecordBatch


def enrich_with_social_signals(batches: Iterable[RecordBatch]) -> RecordBatch:
    """Annotate candidates with synthetic social reach metrics."""

    enriched: RecordBatch = []
    for batch in tqdm(list(batches), desc="social_enrichment", unit="batch"):
        for record in batch:
            updated = dict(record)
            full_name = str(updated.get("player.full_name", ""))
            updated["social.last_check"] = datetime.now(UTC).isoformat(timespec="seconds")
            updated["social.score"] = _heuristic_social_score(full_name)
            enriched.append(updated)
    return enriched


def _heuristic_social_score(full_name: str) -> float:
    name = full_name.lower()
    base = 0.2 if len(name) < 5 else 0.4
    if any(token in name for token in ("de ", "da ", "di ", "van ", "bin ")):
        base += 0.1
    vowels = sum(name.count(v) for v in "aeiou")
    return round(min(1.0, base + (vowels / 20.0)), 3)


__all__ = ["enrich_with_social_signals"]

