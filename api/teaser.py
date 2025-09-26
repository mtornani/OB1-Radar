import json
from pathlib import Path
from typing import Any, Dict


def _load_data() -> Dict[str, Any]:
    data_path = Path("output/daily.json")
    if not data_path.exists():
        data_path = Path("public/data.json")
    if not data_path.exists():
        return {}
    try:
        return json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def handler(request):  # Vercel signature
    data = _load_data()
    items = data.get("items") or []
    if not isinstance(items, list):
        items = []
    regions = 0
    breakdown = data.get("region_breakdown")
    if isinstance(breakdown, dict):
        regions = len(breakdown.keys())

    payload = {
        "found": len(items),
        "top_score": (items[0].get("score") if items else 0) or 0,
        "regions": regions,
        "generated": data.get("generated_at_utc", "unknown"),
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }
