# OB1 Radar

Antisocial U20 talent detector. Predictions run automatically every Monday at 00:01 UTC and hit the public ledger with hashes, timestamps, and confidence intervals. No meetings. No apologies.

## Quickstart
- `python engine/prediction_engine.py` — generate the next set of Monday predictions (use `--dry-run` to preview).
- `python api/accountability.py` — serve the accountability API exposing brutal honesty responses.
- `python main.py` — execute the legacy Oriundi pipeline if you still want the raw scouting output.
- `python -m engine.prediction_engine` automatically populates an offline X queue in `ledger/posts/` ready to broadcast with `#OB1Predicted` once credentials exist.

Public ledger snapshots live in `ledger/public/latest.json`. Track record accuracy updates each time a prediction resolves.

## Broadcasting without credentials

Each committed run appends ready-to-post copies of the predictions to `ledger/posts/queue.jsonl`. Once X/Twitter credentials exist,
load them in a script and call `XPoster().flush(client=your_client)` to publish and automatically archive the post hashes to
`ledger/posts/sent.jsonl`.
