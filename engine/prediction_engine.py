"""Weekly prediction engine that mints timestamped calls and posts to X.

Triggered Monday 00:01 UTC. Pulls the last weekend of anomaly snapshots,
translates them into bold value predictions and stores proofs via
``PredictionTracker``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from engine.accountability import PredictionPayload, PredictionTracker
from engine.x_poster import XPoster

REGION_BASE_VALUE = {
    "africa": 450_000,
    "asia": 600_000,
    "south-america": 900_000,
    "international": 1_200_000,
    "unknown": 650_000,
}

TIMEFRAME_DAYS = 180  # 6 months horizon for value calls


@dataclass
class CandidateSignal:
    player_id: str
    player_name: str
    label: str
    score: float
    anomaly_type: str
    tags: List[str]
    links: List[str]
    region: str
    source_snapshot: str


class PredictionEngine:
    def __init__(
        self,
        tracker: PredictionTracker,
        poster: Optional[XPoster] = None,
        output_path: str | Path = "output/predictions/latest_predictions.json",
    ) -> None:
        self.tracker = tracker
        self.poster = poster or XPoster()
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def run(
        self,
        limit: int = 3,
        as_of: Optional[datetime] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        as_of = as_of or datetime.now(timezone.utc)
        signals = self._load_weekend_signals(as_of)
        candidates = self._score_candidates(signals)
        top = candidates[:limit]

        minted: List[Dict[str, Any]] = []
        for cand in top:
            payload = self._build_payload(cand, as_of)
            if dry_run:
                record = {
                    "dry_run": True,
                    "payload": payload.to_dict(),
                }
            else:
                record = self.tracker.make_prediction(payload).to_public_dict()
            minted.append(record)

        ledger = self.tracker.export_public_ledger()
        self._write_latest(minted, ledger, dry_run=dry_run)

        if not dry_run:
            self._broadcast(top, minted, ledger)

        return {"predictions": minted, "ledger": ledger}

    # ------------------------------------------------------------------
    def _load_weekend_signals(self, as_of: datetime) -> List[CandidateSignal]:
        weekend_dates = self._weekend_dates(as_of.date())
        snapshots = self._load_snapshots(weekend_dates)
        if not snapshots:
            fallback = self._load_fallback()
            if fallback:
                return fallback
            raise FileNotFoundError("No weekend snapshots available for prediction engine")

        signals: List[CandidateSignal] = []
        for path, data in snapshots:
            for item in data.get("items", []):
                if (item.get("entity") or "").upper() != "PLAYER":
                    continue
                label = str(item.get("label") or "").strip()
                if not label:
                    continue
                player_id = self._slugify(label)
                tags = [str(t).lower() for t in (item.get("why") or [])]
                region = self._infer_region(tags)
                links = [str(l) for l in (item.get("links") or []) if l]
                signals.append(
                    CandidateSignal(
                        player_id=player_id,
                        player_name=label,
                        label=label,
                        score=float(item.get("score", 0.0)),
                        anomaly_type=str(item.get("anomaly_type") or ""),
                        tags=tags,
                        links=links,
                        region=region,
                        source_snapshot=Path(path).name,
                    )
                )
        signals.sort(key=lambda s: s.score, reverse=True)
        return signals

    def _load_snapshots(self, weekend_dates: Sequence[date]) -> List[tuple[str, Dict[str, Any]]]:
        out: List[tuple[str, Dict[str, Any]]] = []
        pattern = Path("docs").glob("daily-*.json")
        for path in sorted(pattern):
            try:
                snap_date = datetime.strptime(path.stem.split("-", 1)[-1], "%Y-%m-%d").date()
            except ValueError:
                continue
            if snap_date not in weekend_dates:
                continue
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            out.append((path.as_posix(), data))
        # Also consider docs/daily.json if no date-specific file for Monday
        live_path = Path("docs/daily.json")
        if live_path.exists():
            with live_path.open(encoding="utf-8") as f:
                data = json.load(f)
            generated = data.get("generated_at_utc")
            if generated:
                try:
                    gen_date = datetime.fromisoformat(generated.replace("Z", "+00:00")).date()
                except ValueError:
                    gen_date = None
                if gen_date and gen_date in weekend_dates:
                    out.append((live_path.as_posix(), data))
        return out

    def _load_fallback(self) -> List[CandidateSignal]:
        fallback_path = Path("data/sample_weekend_signals.json")
        if not fallback_path.exists():
            return []
        with fallback_path.open(encoding="utf-8") as f:
            data = json.load(f)
        signals = []
        for item in data.get("signals", []):
            signals.append(
                CandidateSignal(
                    player_id=str(item.get("player_id")),
                    player_name=str(item.get("player_name")),
                    label=str(item.get("player_name")),
                    score=float(item.get("score", 0.0)),
                    anomaly_type=str(item.get("anomaly_type") or ""),
                    tags=[str(t).lower() for t in (item.get("tags") or [])],
                    links=[str(l) for l in (item.get("links") or []) if l],
                    region=str(item.get("region") or "unknown"),
                    source_snapshot=fallback_path.name,
                )
            )
        signals.sort(key=lambda s: s.score, reverse=True)
        return signals

    def _score_candidates(self, candidates: Iterable[CandidateSignal]) -> List[CandidateSignal]:
        scored = []
        seen_ids: set[str] = set()
        for cand in candidates:
            if cand.player_id in seen_ids:
                continue
            seen_ids.add(cand.player_id)
            scored.append(cand)
        return scored

    def _build_payload(self, cand: CandidateSignal, as_of: datetime) -> PredictionPayload:
        region = cand.region or "unknown"
        base_value = REGION_BASE_VALUE.get(region, REGION_BASE_VALUE["unknown"])
        score = max(0.0, min(100.0, cand.score))

        volatility = 0.25 + (score - 50) / 160
        if "mercato" in cand.tags or "transfer" in cand.tags:
            volatility += 0.1
        if "esordio" in cand.tags or "debut" in cand.tags:
            volatility += 0.06
        if cand.anomaly_type.upper() == "TRANSFER_SIGNAL":
            volatility += 0.08
        volatility = max(0.12, min(0.65, volatility))

        current_value = base_value * (0.55 + score / 160)
        predicted_value = current_value * (1 + volatility)

        confidence = max(0.55, min(0.93, 0.62 + (score - 40) / 180))
        if "unknown" == region:
            confidence -= 0.05
        confidence = round(confidence, 4)

        spread = max(0.05, (1.0 - confidence) * 0.75)
        ci_lower = predicted_value * (1 - spread)
        ci_upper = predicted_value * (1 + spread)

        rationale = {
            "verdict": self._verdict_text(volatility),
            "explanation": self._explanation(cand),
            "prediction": f"Value will move {volatility * 100:.0f}% in {TIMEFRAME_DAYS // 30} months",
            "confidence_interval_pct": [round((1 - spread) * 100, 2), round((1 + spread) * 100, 2)],
            "confidence": confidence,
            "source_snapshot": cand.source_snapshot,
            "tags": cand.tags,
        }

        call_to_action = "Ignore this call and we'll publicly log you when it lands."

        payload = PredictionPayload(
            player_id=cand.player_id,
            player_name=cand.player_name,
            current_value_eur=current_value,
            predicted_value_eur=predicted_value,
            timeframe_days=TIMEFRAME_DAYS,
            rationale=rationale,
            confidence=confidence,
            confidence_interval_eur={"lower": ci_lower, "upper": ci_upper},
            links=cand.links,
            region=region,
            anomaly_type=cand.anomaly_type,
            evidence_score=score,
            created_at_utc=as_of.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
            public_release_at_utc=(as_of + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            call_to_action=call_to_action,
        )
        return payload

    def _broadcast(self, candidates: Sequence[CandidateSignal], minted: Sequence[Dict[str, Any]], ledger: Dict[str, Any]) -> None:
        if not candidates:
            return
        accuracy = ledger.get("accuracy_pct")
        track_line = "Track record: no verifications yet" if accuracy is None else f"Track record: {accuracy}% accuracy on {ledger.get('verified_predictions', 0)} predictions"
        for cand, record in zip(candidates, minted):
            payload = record.get("payload", {})
            confidence = payload.get("confidence", 0) * 100
            growth_pct = ((payload.get("predicted_value_eur", 0) - payload.get("current_value_eur", 0)) / max(payload.get("current_value_eur", 1), 1)) * 100
            text = (
                f"#OB1Predicted — {cand.player_name}: {confidence:.0f}% probability of a {growth_pct:.0f}% swing within 6 months. "
                f"Current €{payload.get('current_value_eur', 0)/1_000_000:.2f}M → €{payload.get('predicted_value_eur', 0)/1_000_000:.2f}M. {track_line}"
            )
            meta = {
                "hash": record.get("hash"),
                "links": cand.links,
                "region": cand.region,
                "anomaly_type": cand.anomaly_type,
            }
            self.poster.post(text, meta)

    def _write_latest(self, minted: Sequence[Dict[str, Any]], ledger: Dict[str, Any], dry_run: bool) -> None:
        payload = {
            "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dry_run": dry_run,
            "predictions": minted,
            "ledger_snapshot": ledger,
        }
        with self.output_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _weekend_dates(as_of: date) -> List[date]:
        weekday = as_of.weekday()
        monday = as_of - timedelta(days=weekday)
        saturday = monday - timedelta(days=2)
        sunday = monday - timedelta(days=1)
        return [saturday, sunday, monday]

    @staticmethod
    def _infer_region(tags: Iterable[str]) -> str:
        for region in ("africa", "asia", "south-america", "international"):
            if region in tags:
                return region
        return "unknown"

    @staticmethod
    def _slugify(label: str) -> str:
        slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in label)
        slug = '-'.join(filter(None, slug.split('-')))
        return slug[:80] or "unknown-player"

    @staticmethod
    def _verdict_text(volatility: float) -> str:
        pct = volatility * 100
        if pct >= 40:
            return f"Overvalued by {pct:.0f}%"
        if pct >= 20:
            return f"Value swing {pct:.0f}% incoming"
        return f"Margin shift {pct:.0f}%"

    @staticmethod
    def _explanation(cand: CandidateSignal) -> str:
        tags = ', '.join(sorted(set(cand.tags)))
        return f"Signal: {cand.anomaly_type} — tags [{tags}]"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OB1 Monday prediction engine")
    parser.add_argument("--limit", type=int, default=3, help="How many predictions to mint")
    parser.add_argument("--dry-run", action="store_true", help="Compute without writing predictions")
    parser.add_argument(
        "--as-of",
        type=str,
        help="ISO date/time override (UTC). Example: 2025-01-06T00:01:00Z",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    tracker = PredictionTracker()
    poster = XPoster()
    engine = PredictionEngine(tracker=tracker, poster=poster)

    as_of = None
    if args.as_of:
        as_of = datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
    result = engine.run(limit=args.limit, as_of=as_of, dry_run=args.dry_run)

    print(json.dumps({"status": "ok", "predictions": len(result.get("predictions", []))}))


if __name__ == "__main__":  # pragma: no cover
    main()
