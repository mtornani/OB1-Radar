"""Minimal X/Twitter posting helper.

We post aggressively when credentials exist, otherwise queue messages so humans
can't claim we never tried."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime(ISO_FORMAT)


@dataclass
class PostResult:
    status: str
    detail: str
    response: Optional[Dict[str, Any]] = None


class XPoster:
    """Posts predictions to X/Twitter or queues them if credentials are missing."""

    API_URL = "https://api.x.com/2/tweets"

    def __init__(
        self,
        bearer_token: Optional[str] = None,
        queue_path: str | Path = "output/predictions/x_queue.jsonl",
    ) -> None:
        self.bearer_token = bearer_token or os.getenv("X_BEARER_TOKEN") or os.getenv("TWITTER_BEARER_TOKEN")
        self.queue_path = Path(queue_path)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)

    def can_post(self) -> bool:
        return bool(self.bearer_token)

    def post(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> PostResult:
        payload = {"text": text}
        metadata = metadata or {}
        if not self.can_post():
            self._queue("missing_credentials", payload, metadata)
            return PostResult(status="queued", detail="missing_credentials")
        if requests is None:
            self._queue("requests_missing", payload, metadata)
            return PostResult(status="queued", detail="requests_missing")

        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(self.API_URL, headers=headers, json=payload, timeout=30)
        except Exception as exc:  # pragma: no cover - network error path
            self._queue(f"error:{exc}", payload, metadata)
            return PostResult(status="queued", detail=f"network_error:{exc}")

        if resp.status_code >= 400:
            detail = f"http_{resp.status_code}"
            self._queue(detail, payload, {**metadata, "response": resp.text[:400]})
            return PostResult(status="queued", detail=detail, response=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None)

        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}
        return PostResult(status="posted", detail="ok", response=data)

    def _queue(self, reason: str, payload: Dict[str, Any], metadata: Dict[str, Any]) -> None:
        record = {
            "reason": reason,
            "payload": payload,
            "metadata": metadata,
            "queued_at_utc": _utcnow_iso(),
        }
        with self.queue_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


__all__ = ["XPoster", "PostResult"]
