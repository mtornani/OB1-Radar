"""Local historical call-up ingestion."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .base import DataSource, RecordBatch, SourceMetadata
from ..config import HistoricalRosterSettings


class HistoricalRosterSource(DataSource):
    """Loads recent FSGC call-up history from a CSV maintained offline."""

    def __init__(self, settings: HistoricalRosterSettings) -> None:
        self.settings = settings

    def fetch(self) -> Iterable[RecordBatch]:
        if not self.settings.enabled:
            return []

        path = Path(self.settings.path)
        if not path.exists():
            return []

        batch: RecordBatch = []
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for idx, row in enumerate(reader):
                if idx >= max(self.settings.max_rows, 0):
                    break
                batch.append(self._build_record(row))

        return [batch] if batch else []

    def _build_record(self, row: dict) -> dict:
        cleaned = {key: (row.get(key, "") or "").strip() for key in row.keys()}
        record = {
            "player.full_name": cleaned.get("player_name", ""),
            "player.birth_date": cleaned.get("birth_date", ""),
            "player.birth_place": cleaned.get("birth_place", ""),
            "player.current_club": cleaned.get("current_club", ""),
            "player.position": cleaned.get("position", ""),
            "article.url": cleaned.get("source_url", ""),
            "article.text": cleaned.get("scouting_notes", ""),
            "fsgc.team_level": cleaned.get("team_level", ""),
            "fsgc.call_up_date": cleaned.get("call_up_date", ""),
            "fsgc.opponent": cleaned.get("opponent", ""),
        }
        record["__metadata__"] = SourceMetadata(
            source="historical_callups",
            retrieved_at=datetime.now(UTC),
            confidence=0.6,
        )
        return record


__all__ = ["HistoricalRosterSource"]

