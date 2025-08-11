#!/usr/bin/env python3
# OB1 • Anomaly Radar — engine/run.py
# Fonte dati (priorità): Google Sheet CSV -> AnyCrawl API -> fallback demo

import os, json, csv, io, requests
from datetime import datetime

# --- ENV / CONFIG ------------------------------------------------------------
API_URL  = os.getenv("ANYCRAWL_API_URL", "https://api.anycrawl.dev").rstrip("/")
API_KEY  = os.getenv("ANYCRAWL_API_KEY", "")          # ok anche "dummy-value"
SHEET_CSV_URL = os.getenv("SHEET_CSV_URL", "").strip()  # opzionale

HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["Authorization"] = f"Bearer {API_KEY}"

# --- HELPERS -----------------------------------------------------------------
def ac_post(path: str, payload: dict):
    """POST all'API AnyCrawl, ma non fa fallire il run: ritorna None se c'è errore."""
    url = f"{API_URL}{path}"
    try:
        r = requests.post(url, headers=HEADERS, json=payload, timeout=45)
        if r.status_code >= 400:
            return None
        return r.json()
    except Exception:
        return None

def search(query: str, pages: int = 1, lang: str = "it"):
    return ac_post("/v1/search", {"query": query, "pages": pages, "lang": lang})

def scrape(url: str, engine: str = "cheerio"):
    return ac_post("/v1/scrape", {"url": url, "engine": engine, "formats": ["markdown","text"]})

def items_from_sheet(csv_url: str):
    """Legge una Google Sheet pubblicata come CSV e la mappa in items Top-10."""
    r = requests.get(csv_url, timeout=20)
    r.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r.text)))
    items = []
    for row in rows:
        items.append({
            "entity": (row.get("entity") or "PLAYER").upper(),
            "label":  (row.get("label")  or "Sconosciuto")[:60],
            "anomaly_type": (row.get("anomaly_type") or "NOISE_PULSE").upper(),
            "score": int(float(row.get("score", "50"))),
            "why":   [w.strip() for w in (row.get("why","")).split(";") if w.strip()] or ["from sheet"],
            "links": [row.get("link") or "https://mtornani.github.io/OB1-Radar/"]
        })
    # Top-10 per score
    return sorted(items, key=lambda x: x["score"], reverse=True)[:10]

def fallback_items():
    base = "https://github.com/mtornani/OB1-Radar"
    items = []
    for i in range(1, 11):
        items.append({
            "entity": "PLAYER",
            "label": f"Demo anomaly #{i}",
            "anomaly_type": "NOISE_PULSE",
            "score": max(5, 100 - i*7),
            "why": ["fallback mode (no API response)"],
            "links": [base]
        })
    return items

# --- MAIN --------------------------------------------------------------------
def main():
    items = []

    # 1) Prova Sorgente CSV (mobile-friendly)
    if SHEET_CSV_URL:
        try:
            items = items_from_sheet(SHEET_CSV_URL)
        except Exception:
            items = []

    # 2) Se la Sheet non c'è o è vuota, prova AnyCrawl
    if not items:
        serp = search("talento calcio U19 emergente", pages=1, lang="it")
        results = []
        if serp:
            results = (serp.get("data") or serp.get("results") or [])
            results = [r for r in results if r.get("url")][:5]

        for r in results:
            url = r["url"]
            page = scrape(url) or {}
            data = page.get("data") or {}
            text = (data.get("markdown") or data.get("text") or "")[:20000].lower()

            # scoring minimale per MVP
            score = 0.0
            for k, w in [("gol",2.0), ("assist",1.5), ("under",1.2), ("u19",1.2), ("transfer",1.4), ("scouting",1.1)]:
                score += w * text.count(k)
            score = max(0, min(100, round(score, 2)))

            why = []
            if "under" in text or "u19" in text:   why.append("età/giovanile")
            if "transfer" in text or "mercato" in text: why.append("rumore mercato")
            if "gol" in text or "assist" in text:  why.append("segnale prestazionale")
            if not why: why = ["pattern testuale"]

            items.append({
                "entity": "PLAYER",
                "label": (r.get("title") or "Sconosciuto")[:60],
                "anomaly_type": "NOISE_PULSE",
                "score": score,
                "why": list(set(why)),
                "links": [url]
            })

    # 3) Se ancora niente, fallback certo
    if not items:
        items = fallback_items()

    # 4) Ordina e salva
    items = sorted(items, key=lambda x: x["score"], reverse=True)[:10]
    payload = {
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source": "OB1-AnomalyRadar",
        "items": items
    }

    os.makedirs("output", exist_ok=True)
    with open("output/daily.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"OK: wrote output/daily.json with {len(items)} items")

if __name__ == "__main__":
    main()
