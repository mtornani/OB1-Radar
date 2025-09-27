"""Public accountability API for OB1 predictions."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.prediction_tracker import PredictionTracker

app = Flask(__name__)
tracker = PredictionTracker()


@app.route("/api/predictions", methods=["GET"])
def list_predictions() -> Any:
    records = tracker.list_predictions()
    snapshot_path = tracker.export_public_snapshot()
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    payload = [
        {
            "hash": record.hash,
            "player": record.player_name,
            "player_name": record.player_name,
            "probability": record.probability,
            "confidence_interval": record.confidence_interval,
            "timeframe": record.timeframe,
            "verdict": (
                "Burst imminent" if record.probability > 0.7 else "Trajectory rising"
            ),
            "timestamp": record.timestamp,
        }
        for record in records
    ]
    return jsonify({
        "status": "brutal_honesty",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "predictions": payload,
        "track_record": snapshot["track_record"],
    })


@app.route("/api/predictions/<prediction_hash>", methods=["GET"])
def get_prediction(prediction_hash: str) -> Any:
    for record in tracker.list_predictions():
        if record.hash == prediction_hash:
            return jsonify(
                {
                    "status": "brutal_honesty",
                    "prediction": {
                        "hash": record.hash,
                        "player": record.player_name,
                        "probability": record.probability,
                        "confidence_interval": record.confidence_interval,
                        "timeframe": record.timeframe,
                        "rationale": record.rationale,
                        "snapshot": record.source_snapshot,
                    },
                }
            )
    abort(404)


@app.route("/api/track-record", methods=["GET"])
def get_track_record() -> Any:
    snapshot = tracker.export_public_snapshot(limit=25)
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    return jsonify(data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

