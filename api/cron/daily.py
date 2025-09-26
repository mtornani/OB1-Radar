import json
import subprocess
from typing import Any, Dict


def handler(request) -> Dict[str, Any]:  # Vercel signature
    try:
        result = subprocess.run(["python", "run.py"], check=False, capture_output=True, text=True)
        body = {
            "status": "success" if result.returncode == 0 else "failure",
            "returncode": result.returncode,
            "output": (result.stdout or "")[-500:],
            "error": (result.stderr or "")[-500:],
        }
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body),
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "error", "error": str(exc)}),
        }
