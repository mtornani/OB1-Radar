"""Open data registry ingestion."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Iterable, Optional
from urllib import request, parse

from .base import DataSource, RecordBatch, SourceMetadata
from ..config import RegistrySettings


class OpenRegistrySource(DataSource):
    """Fetches civil registry data exposed as CSV/JSON."""

    def __init__(
        self,
        settings: RegistrySettings,
        *,
        opener: Optional[request.OpenerDirector] = None,
    ) -> None:
        self.settings = settings
        self.opener = opener or request.build_opener()

    def fetch(self) -> Iterable[RecordBatch]:
        if not self.settings.enabled or not self.settings.base_url:
            return []

        try:
            url = f"{self.settings.base_url}?{parse.urlencode({'limit': self.settings.max_results})}"
            with self.opener.open(url, timeout=30) as response:
                payload = response.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - network safety
            raise RuntimeError("Impossibile scaricare i registri open data") from exc

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:  # pragma: no cover - data issues
            return []

        records = data if isinstance(data, list) else data.get("results", [])
        if not isinstance(records, list):
            return []

        enriched: RecordBatch = []
        for item in records:
            if not isinstance(item, dict):
                continue
            enriched.append(
                {
                    **item,
                    "__metadata__": SourceMetadata(
                        source="open_registry",
                        retrieved_at=datetime.now(UTC),
                        confidence=0.85,
                    ),
                }
            )
        return [enriched]


__all__ = ["OpenRegistrySource"]

