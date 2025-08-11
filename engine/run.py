#!/usr/bin/env python3
import os, json, requests
from datetime import datetime

API_URL = os.getenv("ANYCRAWL_API_URL", "https://api.anycrawl.dev").rstrip("/")
API_KEY = os.getenv("ANYCRAWL_API_KEY", "")
HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["Authorization"] = f"Bearer {API_KEY}"

def ac_post(path, payload):
    """HTTP POST robusta: se fallisce, torna None (non alza)."""
    try:
        r = requests.post(f"{API_URL}{path}", headers=HEADERS, json=payload, timeout=45)
        if r.status_code >= 400:
            return None
        return r.json()
    except Exception:
        return None

def search(query, pages=1, lang="it"):
    return ac_post("/v1/search", {"query": query, "pages": pages, "lang": lang})

def scrape(url, engine="cheerio"):
    return ac_post("/v1/scrape", {"url": url, "engine": engine, "formats": ["markdown","text"]})

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

def main():
    items = []
    # 1) Prova SERP
    serp = search("talento calcio U19 emergente", pages=1, lang="it")
    results = []
    if serp:
        # alcune istanze usano "data", altre "results"
        results = [r for r in (serp.get("data") or serp.get("results") or []) if r.get("url")]
        results = results[:5]

    # 2) Se ho risultati, provo a fare scrape e scoring grezzo
    if results:
        for r in results:
            url = r["url"]
            page = scrape(url)
            text = ""
            if page:
                data = page.get("data") or {}
                text = (data.get("markdown") or data.get("text") or "")[:20000].lower()

            # se anche lo scrape fallisce, continuo ma con testo vuoto
            score = 0
            for k, w in [("gol", 2.0), ("assist", 1.5), ("under", 1.2), ("u19", 1.2), ("transfer", 1.4), ("scouting", 1.1)]:
                score += w * text.count(k)
            score = max(0, min(100, round(score, 2)))

            why = []
            if "under" in text or "u19" in text:   why.append("età/giovanile")
            if "transfer" in text or "mercato" in text: why.append("rumore mercato")
            if "gol" in text or "assist" in text:  why.append("segnale prestazionale")
            if not why: why = ["pattern testuale o link rilevante"]

            items.append({
                "entity": "PLAYER",
                "label": (r.get("title") or "Sconosciuto")[:60],
                "anomaly_type": "NOISE_PULSE",
                "score": score,
                "why": list(set(why)),
                "links": [url]
            })

    # 3) Se non ho nulla, uso fallback stabile (10 elementi)
    if not items:
        items = fallback_items()

    # 4) Ordina e salva
    items = sorted(items, key=lambda x: x["score"], reverse=True)[:10]
    payload = {
        "stamp": datetime.utcnow().strftime("%Y-%m-%d"),
        "source": "OB1-AnomalyRadar",
        "items": items
    }
    os.makedirs("output", exist_ok=True)
    with open("output/daily.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"OK: wrote output/daily.json with {len(items)} items")

if __name__ == "__main__":
    main()