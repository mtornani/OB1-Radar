"""Prediction tracking utilities for OB1."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass
class PredictionRecord:
    """Immutable prediction payload stored on disk."""

    hash: str
    timestamp: str
    player_id: str
    player_name: str
    current_value_eur: Optional[float]
    predicted_value_eur: Optional[float]
    timeframe: str
    probability: float
    confidence_interval: List[float]
    rationale: List[str]
    source_snapshot: str


@dataclass
class VerificationRecord:
    """Outcome captured after a prediction resolves."""

    prediction_hash: str
    observed_at: str
    observed_value_eur: Optional[float]
    verdict: str
    notes: List[str]


class PredictionTracker:
    """Handles persistence of predictions and verification results."""

    def __init__(self, ledger_dir: Path | str = "ledger") -> None:
        self.ledger_dir = Path(ledger_dir)
        self.predictions_dir = self.ledger_dir / "predictions"
        self.verifications_dir = self.ledger_dir / "verifications"
        self.public_dir = self.ledger_dir / "public"
        self.index_path = self.ledger_dir / "index.json"
        self.verifications_index_path = self.ledger_dir / "verifications.json"

        for path in (
            self.ledger_dir,
            self.predictions_dir,
            self.verifications_dir,
            self.public_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

        if not self.index_path.exists():
            self.index_path.write_text("[]\n", encoding="utf-8")
        if not self.verifications_index_path.exists():
            self.verifications_index_path.write_text("[]\n", encoding="utf-8")

    # ------------------------------------------------------------------
    # Prediction lifecycle
    # ------------------------------------------------------------------
    def make_prediction(
        self,
        *,
        player_id: str,
        player_name: str,
        current_value_eur: Optional[float],
        predicted_value_eur: Optional[float],
        timeframe: str,
        probability: float,
        confidence_interval: Iterable[float],
        rationale: Iterable[str],
        source_snapshot: str,
        persist: bool = True,
    ) -> PredictionRecord:
        """Create and optionally persist a prediction record."""

        timestamp = datetime.now(timezone.utc).strftime(ISO_FORMAT)
        payload = {
            "timestamp": timestamp,
            "player_id": player_id,
            "player_name": player_name,
            "current_value_eur": current_value_eur,
            "predicted_value_eur": predicted_value_eur,
            "timeframe": timeframe,
            "probability": float(probability),
            "confidence_interval": [float(x) for x in confidence_interval],
            "rationale": list(rationale),
            "source_snapshot": source_snapshot,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        record = PredictionRecord(hash=digest, **payload)

        if persist:
            self._store_prediction(record)
            self.export_public_snapshot()
        return record

    def verify_prediction(
        self,
        *,
        prediction_hash: str,
        observed_value_eur: Optional[float],
        verdict: str,
        notes: Iterable[str],
        persist: bool = True,
    ) -> VerificationRecord:
        """Persist a verification result for an existing prediction."""

        observed_at = datetime.now(timezone.utc).strftime(ISO_FORMAT)
        record = VerificationRecord(
            prediction_hash=prediction_hash,
            observed_at=observed_at,
            observed_value_eur=observed_value_eur,
            verdict=verdict,
            notes=list(notes),
        )

        if persist:
            self._store_verification(record)
            self.export_public_snapshot()
        return record

    def list_predictions(self) -> List[PredictionRecord]:
        """Return all tracked predictions ordered newest first."""

        return [
            PredictionRecord(**entry)
            for entry in self._read_json(self.index_path)
        ]

    def list_verifications(self) -> List[VerificationRecord]:
        """Return all verification records ordered newest first."""

        return [
            VerificationRecord(**entry)
            for entry in self._read_json(self.verifications_index_path)
        ]

    def export_public_snapshot(self, limit: int = 12) -> Path:
        """Emit a public JSON snapshot of recent predictions and verifications."""

        snapshot = {
            "generated_at": datetime.now(timezone.utc).strftime(ISO_FORMAT),
            "predictions": [
                asdict(record)
                for record in self.list_predictions()[:limit]
            ],
            "verifications": [
                asdict(record)
                for record in self.list_verifications()[:limit]
            ],
            "track_record": self._compute_track_record(),
        }

        path = self.public_dir / "latest.json"
        path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _store_prediction(self, record: PredictionRecord) -> None:
        path = self.predictions_dir / f"{record.timestamp.replace(':', '-')}-{record.hash}.json"
        path.write_text(json.dumps(asdict(record), indent=2, sort_keys=True) + "\n", encoding="utf-8")

        index = self._read_json(self.index_path)
        index.insert(0, asdict(record))
        self._write_json(self.index_path, index)

    def _store_verification(self, record: VerificationRecord) -> None:
        path = self.verifications_dir / f"{record.observed_at.replace(':', '-')}-{record.prediction_hash}.json"
        path.write_text(json.dumps(asdict(record), indent=2, sort_keys=True) + "\n", encoding="utf-8")

        index = self._read_json(self.verifications_index_path)
        index.insert(0, asdict(record))
        self._write_json(self.verifications_index_path, index)

    def _compute_track_record(self) -> Dict[str, Any]:
        predictions = self._read_json(self.index_path)
        verifications = self._read_json(self.verifications_index_path)
        total = len(predictions)
        verified = len(verifications)
        verdict_counts: Dict[str, int] = {}
        for verification in verifications:
            verdict = verification.get("verdict", "unknown")
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        accuracy = 0.0
        if verified:
            hits = verdict_counts.get("correct", 0)
            accuracy = hits / verified

        return {
            "total_predictions": total,
            "verified_predictions": verified,
            "accuracy": round(accuracy, 3),
            "verdict_breakdown": verdict_counts,
        }

    @staticmethod
    def _read_json(path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8") or "[]")

    @staticmethod
    def _write_json(path: Path, payload: List[Dict[str, Any]]) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

