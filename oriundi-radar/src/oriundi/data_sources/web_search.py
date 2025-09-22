"""AnyCrawl search integration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Iterable, List, Optional
from urllib import request

from .base import DataSource, RecordBatch, SourceMetadata
from ..config import APISettings


class AnyCrawlSearchSource(DataSource):
    """Executes vertical football searches via AnyCrawl."""

    def __init__(
        self,
        settings: APISettings,
        queries: List[str],
        *,
        opener: Optional[request.OpenerDirector] = None,
        pages: int = 1,
        limit: int = 20,
    ) -> None:
        self.settings = settings
        self.queries = queries
        self.pages = pages
        self.limit = limit
        self.opener = opener or request.build_opener()

    def fetch(self) -> Iterable[RecordBatch]:
        batches: list[RecordBatch] = []
        for query in self.queries:
            payload = json.dumps({"query": query, "pages": self.pages, "limit": self.limit}).encode(
                "utf-8"
            )
            req = request.Request(
                f"{self.settings.base_url}/search",
                data=payload,
                headers=self._headers(),
                method="POST",
            )
            try:
                with self.opener.open(req, timeout=30) as response:
                    data = json.loads(response.read().decode("utf-8"))
            except Exception:  # pragma: no cover - network issues
                continue
            results = data.get("results", []) if isinstance(data, dict) else []
            batch: RecordBatch = []
            for item in results:
                if not isinstance(item, dict):
                    continue
                batch.append(
                    {
                        **item,
                        "__metadata__": SourceMetadata(
                            source="anycrawl_search",
                            retrieved_at=datetime.now(UTC),
                            confidence=0.75,
                        ),
                    }
                )
            if batch:
                batches.append(batch)
        return batches

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.settings.key:
            headers["Authorization"] = f"Bearer {self.settings.key}"
        return headers


__all__ = ["AnyCrawlSearchSource"]

