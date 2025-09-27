"""Offline X poster queue for OB1 predictions."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import hashlib

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass
class QueuedPost:
    """Represents a post queued for X."""

    hash: str
    timestamp: str
    message: str
    tags: List[str]
    player: str
    probability: float
    confidence: List[float]
    timeframe: str


class XPoster:
    """Handles offline queuing of X posts with hashed audit trail."""

    def __init__(self, posts_dir: Path | str = "ledger/posts") -> None:
        self.posts_dir = Path(posts_dir)
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        self.queue_path = self.posts_dir / "queue.jsonl"
        self.sent_path = self.posts_dir / "sent.jsonl"

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------
    def queue_prediction_post(
        self,
        *,
        player: str,
        probability: float,
        confidence_interval: Iterable[float],
        timeframe: str,
        rationale: Iterable[str],
    ) -> QueuedPost:
        """Create and persist a queued post describing the prediction."""

        timestamp = datetime.now(timezone.utc).strftime(ISO_FORMAT)
        tags = ["#OB1Predicted", "#U20Scouting", "#Football"]
        rationale_excerpt = self._format_rationale(rationale)
        message = (
            f"{tags[0]} {player} -> {probability * 100:.0f}% burst odds. "
            f"Confidence {confidence_interval[0] * 100:.0f}-{confidence_interval[1] * 100:.0f}%. "
            f"Timeframe: {timeframe.replace('_', ' ')}. {rationale_excerpt}"
        )
        payload = {
            "timestamp": timestamp,
            "player": player,
            "probability": round(probability, 4),
            "confidence": [round(x, 4) for x in confidence_interval],
            "timeframe": timeframe,
            "message": message,
            "tags": tags,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        post = QueuedPost(
            hash=digest,
            timestamp=timestamp,
            message=message,
            tags=tags,
            player=player,
            probability=round(probability, 4),
            confidence=[round(x, 4) for x in confidence_interval],
            timeframe=timeframe,
        )

        if not self._post_exists(digest):
            self._append_json_line(self.queue_path, {**payload, "hash": digest})
        return post

    def list_queue(self) -> List[QueuedPost]:
        """Return queued posts that are waiting to be published."""

        return [QueuedPost(**entry) for entry in self._read_json_lines(self.queue_path)]

    def list_sent(self) -> List[QueuedPost]:
        """Return posts that have already been marked as sent."""

        return [QueuedPost(**entry) for entry in self._read_json_lines(self.sent_path)]

    # ------------------------------------------------------------------
    # Sending (best-effort; works offline)
    # ------------------------------------------------------------------
    def flush(self, *, client: Optional[object] = None) -> List[QueuedPost]:
        """Attempt to send queued posts.

        If a client implementing ``create_tweet(text=...)`` is provided the posts are
        transmitted. Otherwise they are simply moved to ``sent.jsonl`` so the ledger
        keeps an immutable record that the content was ready.
        """

        queued = self._read_json_lines(self.queue_path)
        if not queued:
            return []

        sent_entries: List[dict] = []
        for entry in queued:
            if client is not None:
                try:
                    client.create_tweet(text=entry["message"])
                except Exception as exc:  # pragma: no cover - best effort only
                    # If sending fails we keep the post in the queue for later.
                    sys.stderr.write(f"Failed to post to X: {exc}\n")
                    continue
            sent_entries.append(entry)

        if sent_entries:
            current = self._read_json_lines(self.sent_path)
            current.extend(sent_entries)
            self._write_json_lines(self.sent_path, current)
            self._write_json_lines(self.queue_path, [])

        return [QueuedPost(**entry) for entry in sent_entries]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _format_rationale(self, rationale: Iterable[str]) -> str:
        items = [str(value).strip() for value in rationale if str(value).strip()]
        if not items:
            return "Signals archived"
        joined = "; ".join(items[:3])
        return joined[:180]

    def _post_exists(self, digest: str) -> bool:
        for path in (self.queue_path, self.sent_path):
            for entry in self._read_json_lines(path):
                if entry.get("hash") == digest:
                    return True
        return False

    def _read_json_lines(self, path: Path) -> List[dict]:
        if not path.exists():
            return []
        entries: List[dict] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    def _append_json_line(self, path: Path, payload: dict) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def _write_json_lines(self, path: Path, entries: List[dict]) -> None:
        if not entries:
            if path.exists():
                path.unlink()
            return
        with path.open("w", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")

