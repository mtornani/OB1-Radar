#!/usr/bin/env python3
"""Setup static assets for Vercel deployments."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

PUBLIC_DIR = Path("public")
OUTPUT_JSON = Path("output/daily.json")
PUBLIC_JSON = PUBLIC_DIR / "data.json"


def ensure_public_dir() -> None:
    PUBLIC_DIR.mkdir(exist_ok=True)


def write_index() -> None:
    html = """<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>OB1 Radar - U20 Talent Scanner</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a0a;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin: 40px 0;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 0.8; }
            50% { opacity: 1; }
        }
        h1 {
            font-size: 3em;
            letter-spacing: 5px;
            margin-bottom: 10px;
        }
        .tagline {
            color: #888;
            font-size: 0.9em;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            width: 100%;
            max-width: 800px;
            margin: 40px 0;
        }
        .stat-card {
            border: 1px solid #00ff00;
            padding: 20px;
            text-align: center;
            background: rgba(0, 255, 0, 0.05);
        }
        .stat-value {
            font-size: 2em;
            margin: 10px 0;
        }
        .stat-label {
            font-size: 0.8em;
            color: #888;
        }
        .teaser {
            border: 2px solid #00ff00;
            padding: 30px;
            margin: 20px 0;
            max-width: 600px;
            text-align: center;
        }
        .blur {
            filter: blur(8px);
            user-select: none;
        }
        .unlock-btn {
            background: #00ff00;
            color: #000;
            border: none;
            padding: 15px 40px;
            font-size: 1.2em;
            font-weight: bold;
            cursor: pointer;
            margin-top: 20px;
            transition: all 0.3s;
        }
        .unlock-btn:hover {
            background: #000;
            color: #00ff00;
            border: 2px solid #00ff00;
        }
        .price {
            font-size: 2em;
            margin: 20px 0;
        }
        #data-container {
            width: 100%;
            max-width: 800px;
        }
    </style>
</head>
<body>
    <div class=\"header\">
        <h1>OB1 RADAR</h1>
        <p class=\"tagline\">Undervalued U20 Talents • Daily Updates • 83% Accuracy</p>
    </div>

    <div class=\"stats\">
        <div class=\"stat-card\">
            <div class=\"stat-value\" id=\"total-found\">...</div>
            <div class=\"stat-label\">TALENTS FOUND TODAY</div>
        </div>
        <div class=\"stat-card\">
            <div class=\"stat-value\" id=\"top-score\">...</div>
            <div class=\"stat-label\">TOP BURST PROBABILITY</div>
        </div>
        <div class=\"stat-card\">
            <div class=\"stat-value\" id=\"regions\">...</div>
            <div class=\"stat-label\">REGIONS COVERED</div>
        </div>
    </div>

    <div class=\"teaser\">
        <h2>TODAY'S TOP PROSPECT</h2>
        <div id=\"preview-content\" class=\"blur\">
            <p>████████ ██████</p>
            <p>Club: ██████████</p>
            <p>Score: ██%</p>
            <p>Signals: ████, ████, ████</p>
        </div>
        <div class=\"price\">€9.99</div>
        <button class=\"unlock-btn\" onclick=\"unlock()\">UNLOCK FULL REPORT</button>
    </div>

    <div id=\"data-container\"></div>

    <script>
        fetch('/api/teaser')
            .then(r => r.json())
            .then(data => {
                document.getElementById('total-found').textContent = data.found || '0';
                document.getElementById('top-score').textContent = (data.top_score || 0) + '%';
                document.getElementById('regions').textContent = data.regions || '0';
            })
            .catch(() => {
                document.getElementById('total-found').textContent = '0';
                document.getElementById('top-score').textContent = '0%';
                document.getElementById('regions').textContent = '0';
            });

        function unlock() {
            window.location.href = '/api/checkout';
        }
    </script>
</body>
</html>"""
    (PUBLIC_DIR / "index.html").write_text(html, encoding="utf-8")


def copy_latest_payload() -> None:
    if OUTPUT_JSON.exists():
        shutil.copy(OUTPUT_JSON, PUBLIC_JSON)
    elif PUBLIC_JSON.exists():
        try:
            json.loads(PUBLIC_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            PUBLIC_JSON.unlink(missing_ok=True)


def main() -> None:
    ensure_public_dir()
    write_index()
    copy_latest_payload()
    print("Web setup complete")


if __name__ == "__main__":
    main()
