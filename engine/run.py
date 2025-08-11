#!/usr/bin/env python3
import os, json, requests
from datetime import datetime

API_URL = os.getenv("ANYCRAWL_API_URL", "https://api.anycrawl.dev").rstrip("/")
API_KEY = os.getenv("ANYCRAWL_API_KEY", "")
HEADERS = {"Content-Type": "application/json", **({"Authorization": f"Bearer {API_KEY}"} if API_KEY else {})}

def ac_post(path, payload):
    r = requests.post(f"{API_URL}{path}", headers=HEADERS, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def search(query, pages=1, lang="it"):
    return ac_post("/v1/search", {"query": query, "pages": pages, "lang": lang})

def scrape(url, engine="cheerio"):
    return ac_post("/v1/scrape", {"url": url, "engine": engine, "formats": ["markdown","text"]})

def main():
    serp = search("talento calcio U19 emergente", pages=1, lang="it")
    results = [r for r in serp.get("data", []) if r.get("url")][:5]

    items = []
    for r in results:
        url = r["url"]
        page = scrape(url)
        text = (page.get("data", {}).get("markdown") or "")[:20000].lower()

        score = 0
        for k, w in [("gol", 2.0), ("assist", 1.5), ("under", 1.2), ("u19", 1.2), ("transfer", 1.4), ("scouting", 1.1)]:
            score += w * text.count(k)
        score = max(0, min(100, round(score, 2)))

        why = []
        if any(term in text for term in ["under", "u19"]):
            why.append("età/giovanile")
        if any(term in text for term in ["transfer", "mercato"]):
            why.append("rumore mercato")
        if any(term in text for term in ["gol", "assist"]):
            why.append("segnale prestazionale")

        items.append({
            "entity": "PLAYER",
            "label": r.get("title", "Sconosciuto")[:60],
            "anomaly_type": "NOISE_PULSE",
            "score": score,
            "why": list(set(why)) or ["pattern testuale"],
            "links": [url]
        })

    items = sorted(items, key=lambda x: x["score"], reverse=True)[:10]
    payload = {"stamp": datetime.utcnow().strftime("%Y-%m-%d"), "source": "OB1-AnomalyRadar", "items": items}

    os.makedirs("output", exist_ok=True)
    with open("output/daily.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote output/daily.json with {len(items)} items")

if __name__ == "__main__":
    main()
