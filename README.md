# OB1 Radar

Antisocial U20 talent detector. Predictions run automatically every Monday at 00:01 UTC and hit the public ledger with hashes, timestamps, and confidence intervals. No meetings. No apologies.

## Quickstart
- `python engine/prediction_engine.py` — generate the next set of Monday predictions (use `--dry-run` to preview).
- `python api/accountability.py` — serve the accountability API exposing brutal honesty responses.
- `python main.py` — execute the legacy Oriundi pipeline if you still want the raw scouting output.

Public ledger snapshots live in `ledger/public/latest.json`. Track record accuracy updates each time a prediction resolves.
