"""Monday prediction engine that feeds the OB1 accountability stack."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.prediction_tracker import PredictionTracker

OUTPUT_PATH = Path("output/daily.json")
FALLBACK_SIGNALS = [
    {
        "player_id": "fallback-01",
        "label": "South America winger",
        "score": 82,
        "region": "south_america",
        "signals": ["youth_debut", "minutes_spike", "transfer_interest"],
        "valuation_eur": 750000,
        "why": [
            "Minutes up 34% since winter",
            "Shot creation up 0.9 per 90",
            "Agent pushing Serie A move",
        ],
    },
    {
        "player_id": "fallback-02",
        "label": "Nordic centre back",
        "score": 74,
        "region": "northern_europe",
        "signals": ["defensive_duels", "ball_progression", "contract_expiring"],
        "valuation_eur": 520000,
        "why": [
            "Top 5% for aerial wins",
            "Progressive passes doubled season-on-season",
            "Contract ends in 2026 - renewal stalled",
        ],
    },
    {
        "player_id": "fallback-03",
        "label": "West African striker",
        "score": 69,
        "region": "west_africa",
        "signals": ["xg_delta", "pressing_actions", "scout_attendance"],
        "valuation_eur": 310000,
        "why": [
            "Non-penalty xG up 0.28 per 90",
            "Pressing volume top 10% in league",
            "Premier League scouts logged twice in two weeks",
        ],
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Monday prediction engine.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Generate predictions without persisting them"
    )
    parser.add_argument(
        "--as-of",
        help="ISO8601 timestamp to treat as run time (defaults to now in UTC)",
    )
    return parser.parse_args()


def load_weekend_signals(path: Path) -> Tuple[List[Dict[str, Any]], str]:
    """Load latest radar output, returning fallback signals if necessary."""

    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("items") or data.get("players") or []
        generated = data.get("generated_at_utc") or data.get("generated_at")
        if not generated:
            generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return items, generated

    return FALLBACK_SIGNALS, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pick_predictions(items: List[Dict[str, Any]], count: int = 3) -> List[Dict[str, Any]]:
    """Choose the boldest predictions from the available items."""

    scored = [
        (float(item.get("score", 0.0)), item)
        for item in items
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)

    return [item for _, item in scored[:count] if item]


def extract_value(item: Dict[str, Any]) -> float | None:
    """Attempt to derive a euro valuation from the record."""

    for key in (
        "valuation_eur",
        "market_value_eur",
        "value_eur",
        "value",
        "valuation",
    ):
        value = item.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def compute_probability(score: float) -> float:
    """Convert OB1 score into a probability on [0, 1]."""

    return max(0.01, min(0.99, score / 100.0))


def confidence_interval(probability: float) -> Tuple[float, float]:
    """Generate a deterministic but non-trivial confidence interval."""

    spread = max(0.03, 0.12 * (1 - probability))
    lower = max(0.0, probability - spread)
    upper = min(1.0, probability + spread)
    return round(lower, 3), round(upper, 3)


def project_value(current: float | None, probability: float) -> float | None:
    """Project a future value using a simple probability uplift."""

    if current is None:
        return None
    uplift = 0.6 if probability > 0.7 else 0.35 if probability > 0.55 else 0.15
    return round(current * (1.0 + uplift), 2)


def build_rationale(item: Dict[str, Any]) -> List[str]:
    """Assemble rationale strings, leaning on stored reasoning when present."""

    reasons = item.get("why") or item.get("signals") or []
    if isinstance(reasons, list):
        return [str(r) for r in reasons][:4]
    return [str(reasons)]


def main() -> int:
    args = parse_args()
    as_of = (
        datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
        if args.as_of
        else datetime.now(timezone.utc)
    )
    tracker = PredictionTracker()
    items, generated_at = load_weekend_signals(OUTPUT_PATH)
    predictions = pick_predictions(items)

    if not predictions:
        predictions = FALLBACK_SIGNALS

    persisted_records = []

    for item in predictions:
        player_id = str(item.get("player_id") or item.get("id") or item.get("label"))
        player_name = str(item.get("label") or item.get("name") or player_id)
        score = float(item.get("score", 0.0))
        probability = compute_probability(score)
        ci_low, ci_high = confidence_interval(probability)
        current_value = extract_value(item)
        projected_value = project_value(current_value, probability)
        timeframe = "6_months" if probability >= 0.55 else "12_months"
        rationale = build_rationale(item)

        record = tracker.make_prediction(
            player_id=player_id,
            player_name=player_name,
            current_value_eur=current_value,
            predicted_value_eur=projected_value,
            timeframe=timeframe,
            probability=probability,
            confidence_interval=(ci_low, ci_high),
            rationale=rationale,
            source_snapshot=generated_at,
            persist=not args.dry_run,
        )
        persisted_records.append(record)

    summary = {
        "status": "brutal_honesty",
        "generated_at": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_snapshot": generated_at,
        "predictions": [
            {
                "hash": record.hash,
                "player": record.player_name,
                "probability": record.probability,
                "confidence_interval": record.confidence_interval,
                "verdict": (
                    "Burst imminent" if record.probability > 0.7 else "Trajectory rising"
                ),
                "timeframe": record.timeframe,
                "rationale": record.rationale,
            }
            for record in persisted_records
        ],
    }

    if not args.dry_run:
        public_md = tracker.public_dir / "ledger.md"
        lines = [
            "# OB1 Prediction Ledger",
            f"Generated at: {summary['generated_at']}",
            "",
        ]
        for entry in summary["predictions"]:
            lines.extend(
                [
                    f"## {entry['player']}",
                    f"- Hash: `{entry['hash']}`",
                    f"- Probability: {entry['probability']:.2f}",
                    f"- Confidence: {entry['confidence_interval'][0]:.2f} – {entry['confidence_interval'][1]:.2f}",
                    f"- Timeframe: {entry['timeframe']}",
                    "- Rationale:",
                ]
            )
            lines.extend([f"  - {reason}" for reason in entry["rationale"]])
            lines.append("")
        public_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

