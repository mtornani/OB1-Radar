"""Prediction accountability utilities for OB1.

Implements the antisocial automation contract defined in `.context.md`:
- Every prediction is hashed with an immutable timestamp proof
- Accuracy is measured publicly
- Anyone ignoring correct calls gets logged for future "told you so" receipts
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _utcnow() -> datetime:
    """Return current UTC time without microseconds for deterministic hashing."""

    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.strftime(ISO_FORMAT)


def _canonical_json(payload: Dict[str, Any]) -> str:
    """Return a canonical JSON string (sorted keys, UTF-8, no whitespace)."""

    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


@dataclass
class PredictionPayload:
    """Structured payload saved before hashing."""

    player_id: str
    player_name: str
    current_value_eur: float
    predicted_value_eur: float
    timeframe_days: int
    rationale: Dict[str, Any]
    confidence: float
    confidence_interval_eur: Dict[str, float]
    links: List[str]
    region: str
    anomaly_type: str
    evidence_score: float
    created_at_utc: str
    tracker_version: str = "1.0"
    premium_release_delay_hours: int = 48
    public_release_at_utc: Optional[str] = None
    call_to_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "current_value_eur": round(float(self.current_value_eur), 2),
            "predicted_value_eur": round(float(self.predicted_value_eur), 2),
            "timeframe_days": self.timeframe_days,
            "rationale": self.rationale,
            "confidence": round(float(self.confidence), 4),
            "confidence_interval_eur": {
                "lower": round(float(self.confidence_interval_eur.get("lower", 0.0)), 2),
                "upper": round(float(self.confidence_interval_eur.get("upper", 0.0)), 2),
            },
            "links": self.links,
            "region": self.region,
            "anomaly_type": self.anomaly_type,
            "evidence_score": round(float(self.evidence_score), 2),
            "created_at_utc": self.created_at_utc,
            "tracker_version": self.tracker_version,
            "premium_release_delay_hours": self.premium_release_delay_hours,
        }
        if self.public_release_at_utc:
            data["public_release_at_utc"] = self.public_release_at_utc
        if self.call_to_action:
            data["call_to_action"] = self.call_to_action
        return data


@dataclass
class PredictionRecord:
    """Immutable prediction record stored on disk."""

    hash: str
    timestamp_utc: str
    payload: Dict[str, Any]
    canonical: str
    path: Path

    def to_public_dict(self) -> Dict[str, Any]:
        data = {
            "hash": self.hash,
            "timestamp_utc": self.timestamp_utc,
            "payload": self.payload,
            "proof": {
                "algorithm": "sha256",
                "canonical_json": self.canonical,
                "hash": self.hash,
            },
            "storage_path": self.path.as_posix(),
        }
        return data


@dataclass
class VerificationRecord:
    """Outcome record for a prediction once reality catches up."""

    prediction_hash: str
    verified_at_utc: str
    outcome: str
    observed_value_eur: Optional[float]
    error_pct: Optional[float]
    accuracy: str
    ignored_by: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    def to_public_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "prediction_hash": self.prediction_hash,
            "verified_at_utc": self.verified_at_utc,
            "outcome": self.outcome,
            "accuracy": self.accuracy,
            "ignored_by": self.ignored_by,
            "sources": self.sources,
        }
        if self.observed_value_eur is not None:
            data["observed_value_eur"] = round(float(self.observed_value_eur), 2)
        if self.error_pct is not None:
            data["error_pct"] = round(float(self.error_pct), 4)
        if self.notes:
            data["notes"] = self.notes
        return data


class PredictionTracker:
    """Persistent tracker that mints hashed predictions and verifies them."""

    def __init__(
        self,
        predictions_dir: str | Path = "data/predictions",
        verifications_dir: str | Path = "data/verifications",
        ledger_path: str | Path = "output/predictions/ledger.json",
        log_path: str | Path = "logs/prediction_tracker.log",
    ) -> None:
        self.predictions_dir = Path(predictions_dir)
        self.verifications_dir = Path(verifications_dir)
        self.ledger_path = Path(ledger_path)
        self.log_path = Path(log_path)
        self.predictions_dir.mkdir(parents=True, exist_ok=True)
        self.verifications_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Minting predictions
    # ------------------------------------------------------------------
    def make_prediction(self, payload: PredictionPayload) -> PredictionRecord:
        timestamp = _iso(_utcnow())
        payload_dict = payload.to_dict()
        payload_dict["timestamp_utc"] = timestamp
        canonical = _canonical_json(payload_dict)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        day_dir = self.predictions_dir / payload_dict["timestamp_utc"][0:10]
        day_dir.mkdir(parents=True, exist_ok=True)
        path = day_dir / f"{digest}.json"

        record_data = {
            "hash": digest,
            "timestamp_utc": timestamp,
            "payload": payload_dict,
            "canonical": canonical,
        }

        # Avoid mutating existing proofs. If the file exists make sure we don't silently overwrite.
        if path.exists():
            raise FileExistsError(f"Prediction hash collision detected: {digest}")

        with path.open("w", encoding="utf-8") as f:
            json.dump(record_data, f, ensure_ascii=False, indent=2)

        self._append_log(
            {
                "event": "prediction_minted",
                "hash": digest,
                "timestamp_utc": timestamp,
                "player_id": payload.player_id,
                "player_name": payload.player_name,
                "predicted_value_eur": payload.predicted_value_eur,
                "confidence": payload.confidence,
            }
        )

        return PredictionRecord(
            hash=digest,
            timestamp_utc=timestamp,
            payload=payload_dict,
            canonical=canonical,
            path=path,
        )

    # ------------------------------------------------------------------
    # Verifications
    # ------------------------------------------------------------------
    def verify_prediction(
        self,
        prediction_hash: str,
        outcome: str,
        observed_value_eur: Optional[float],
        notes: Optional[str] = None,
        ignored_by: Optional[Iterable[str]] = None,
        sources: Optional[Iterable[str]] = None,
    ) -> VerificationRecord:
        prediction_path = self._find_prediction_file(prediction_hash)
        if not prediction_path:
            raise FileNotFoundError(f"Prediction hash {prediction_hash} not found")

        with prediction_path.open(encoding="utf-8") as f:
            prediction_data = json.load(f)

        predicted_value = float(prediction_data["payload"].get("predicted_value_eur", 0.0))
        error_pct: Optional[float] = None
        accuracy = "unknown"
        if observed_value_eur is not None and predicted_value:
            error_pct = (observed_value_eur - predicted_value) / predicted_value
            if abs(error_pct) <= 0.1:
                accuracy = "on_target"
            elif observed_value_eur > predicted_value:
                accuracy = "undershot"
            else:
                accuracy = "overshot"

        record = VerificationRecord(
            prediction_hash=prediction_hash,
            verified_at_utc=_iso(_utcnow()),
            outcome=outcome,
            observed_value_eur=observed_value_eur,
            error_pct=error_pct,
            accuracy=accuracy,
            ignored_by=list(ignored_by or []),
            sources=list(sources or []),
            notes=notes,
        )

        path = self.verifications_dir / f"{prediction_hash}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(record.to_public_dict(), f, ensure_ascii=False, indent=2)

        self._append_log(
            {
                "event": "prediction_verified",
                "hash": prediction_hash,
                "accuracy": accuracy,
                "ignored_by": record.ignored_by,
            }
        )

        return record

    # ------------------------------------------------------------------
    # Ledger export
    # ------------------------------------------------------------------
    def export_public_ledger(self, output_path: Optional[str | Path] = None) -> Dict[str, Any]:
        """Consolidate predictions + verifications into a public JSON ledger."""

        predictions: List[Dict[str, Any]] = []
        for file_path in sorted(self.predictions_dir.glob("**/*.json")):
            with file_path.open(encoding="utf-8") as f:
                record = json.load(f)
            record["storage_path"] = file_path.as_posix()
            predictions.append(record)

        verifications_map: Dict[str, Dict[str, Any]] = {}
        for file_path in sorted(self.verifications_dir.glob("*.json")):
            with file_path.open(encoding="utf-8") as f:
                data = json.load(f)
            verifications_map[file_path.stem] = data

        correct = 0
        verified = 0
        public_predictions: List[Dict[str, Any]] = []
        shame_wall: List[Dict[str, Any]] = []

        for rec in predictions:
            data = {
                "hash": rec.get("hash"),
                "timestamp_utc": rec.get("timestamp_utc"),
                "payload": rec.get("payload"),
                "proof": {
                    "algorithm": "sha256",
                    "canonical_json": rec.get("canonical"),
                    "hash": rec.get("hash"),
                },
                "storage_path": rec.get("storage_path"),
            }
            verification = verifications_map.get(rec.get("hash"))
            if verification:
                data["verification"] = verification
                verified += 1
                if verification.get("accuracy") == "on_target":
                    correct += 1
                if verification.get("ignored_by"):
                    shame_wall.append(
                        {
                            "hash": rec.get("hash"),
                            "player": rec.get("payload", {}).get("player_name"),
                            "ignored_by": verification.get("ignored_by"),
                            "verified_at_utc": verification.get("verified_at_utc"),
                            "notes": verification.get("notes"),
                        }
                    )
            public_predictions.append(data)

        accuracy_pct = round((correct / verified) * 100, 2) if verified else None

        ledger = {
            "generated_at_utc": _iso(_utcnow()),
            "total_predictions": len(public_predictions),
            "verified_predictions": verified,
            "on_target_predictions": correct,
            "accuracy_pct": accuracy_pct,
            "predictions": public_predictions,
            "shame_wall": shame_wall,
        }

        path = Path(output_path) if output_path else self.ledger_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2)

        # Mirror to docs for public GET (no auth)
        docs_path = Path("docs/prediction-ledger.json")
        docs_path.parent.mkdir(parents=True, exist_ok=True)
        with docs_path.open("w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2)

        return ledger

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _append_log(self, event: Dict[str, Any]) -> None:
        event = {**event, "logged_at_utc": _iso(_utcnow())}
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _find_prediction_file(self, prediction_hash: str) -> Optional[Path]:
        candidates = list(self.predictions_dir.glob(f"**/{prediction_hash}.json"))
        if not candidates:
            return None
        if len(candidates) > 1:
            raise RuntimeError(f"Multiple prediction files found for hash {prediction_hash}")
        return candidates[0]


__all__ = ["PredictionTracker", "PredictionPayload", "PredictionRecord", "VerificationRecord"]
