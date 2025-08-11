#!/usr/bin/env python3
# OB1 • Ouroboros Radar — engine/run.py
# Fonte dati: AnyCrawl /v1/search + /v1/scrape → filtri anti-rumore → Top-10

import os, json, re, requests
from datetime import datetime
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# ---- Config -----------------------------------------------------------------
API_URL = os.getenv("ANYCRAWL_API_URL", "https://api.anycrawl.dev").rstrip("/")
API_KEY = os.getenv("ANYCRAWL_API_KEY", "")

HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["Authorization"] = f"Bearer {API_KEY}"

# Query “calcio giovanile” (variazioni per pescare segnali veri)
QUERIES = [
    "calcio U19 emergente",
    "primavera gol assist U19",
    "debutto esordio serie A U19",
    "transfer ufficiale primavera",
    "nazionale U19 convocati calcio",
]

MAX_SERP = 14           # candidati massimi dalla SERP
MAX_PER_HOST = 2        # evita domini monopolisti
MIN_TEXT_LEN = 600      # scarta pagine troppo corte
TIMEOUT_S = 50

# blocca file/estensioni rumorose
BLOCK_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".zip", ".rar")
# blocca domini/percorsi off-topic
OFF_PATTERNS = (
    "/basket", "/pallacanestro", "volley", "rugby", "/economia", "/politica", "/motori",
    "almanacco", "forumfree", "wikipedia.org", "facebook.com", "instagram.com", "tiktok.com",
)

# segnali “positivi” (conteggio parole chiave con pesi)
POS_WEIGHTS = {
    r"\bgol\b": 2.0,
    r"\bassist\b": 1.6,
    r"\bunder\b": 1.2,
    r"\bu19\b": 1.2,
    r"\bprimavera\b": 1.3,
    r"\besordio\b|\bdebutto\b": 2.2,
    r"\btransfer\b|\bmercato\b|\bingaggio\b|\bprestito\b": 1.5,
    r"\bnazionale\b": 1.6,
}

# almeno uno di questi deve comparire per considerare “calcio”
MUST_HAVE_ANY = ("calcio", "football", "primavera", "serie a", "serie b", "u19", "u17")

# ---- AnyCrawl client helpers -------------------------------------------------
def ac_post(path: str, payload: dict):
    """POST robusto verso AnyCrawl. Ritorna dict o None."""
    try:
        r = requests.post(f"{API_URL}{path}", headers=HEADERS, json=payload, timeout=TIMEOUT_S)
        if r.status_code >= 400:
            print(f"[AnyCrawl] {path} HTTP {r.status_code} :: {r.text[:200]}")
            return None
        return r.json()
    except Exception as e:
        print(f"[AnyCrawl] error {path}: {e}")
        return None

def ac_search(query: str, pages: int = 1, limit: int = 20, lang: str = "it"):
    # se la tua istanza espone /v1/search (come nel dashboard), usiamo quello
    return ac_post("/v1/search", {"query": query, "pages": pages, "limit": limit, "lang": lang})

def ac_scrape(url: str, engine: str = "playwright"):
    # playwright è più affidabile per siti dinamici; formati: markdown+text
    return ac_post("/v1/scrape", {"url": url, "engine": engine, "formats": ["markdown", "text"]})

# ---- Utilities ---------------------------------------------------------------
def normalize_url(u: str) -> str:
    """normalizza: rimuove frammenti, utm, ordina query."""
    p = urlparse(u)
    if not p.scheme:
        return u
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    return urlunparse((p.scheme, p.netloc.lower(), p.path, "", urlencode(sorted(q)), ""))

def allowed_url(u: str) -> bool:
    lu = u.lower()
    if any(lu.endswith(ext) for ext in BLOCK_EXT):
        return False
    if any(tok in lu for tok in OFF_PATTERNS):
        return False
    return True

def text_from_page(scrape_json: dict) -> str:
    if not scrape_json:
        return ""
    data = scrape_json.get("data") or {}
    t = data.get("markdown") or data.get("text") or ""
    return t if isinstance(t, str) else ""

def good_text(txt: str) -> bool:
    t = txt.lower()
    if len(t) < MIN_TEXT_LEN:
        return False
    if not any(k in t for k in MUST_HAVE_ANY):
        return False
    # evita testi pieni di navigazione/privacy
    nav_noise = sum(t.count(w) for w in ("cookie", "privacy", "accetta", "banner", "newsletter"))
    return nav_noise < 15

def score_text(txt: str) -> float:
    t = txt.lower()
    score = 0.0
    for pat, w in POS_WEIGHTS.items():
        score += w * len(re.findall(pat, t))
    return float(max(0, min(100, round(score, 2))))

def infer_type(txt: str) -> str:
    t = txt.lower()
    if re.search(r"\besordio\b|\bdebutto\b", t):
        return "PLAYER_BURST"
    if re.search(r"\btransfer\b|\bmercato\b|\bprestito\b|\bingaggio\b", t):
        return "TRANSFER_SIGNAL"
    return "NOISE_PULSE"

# ---- Pipeline ----------------------------------------------------------------
def collect_candidates():
    """SERP → lista di (title, url) già filtrati e deduplicati."""
    seen_urls, per_host = set(), {}
    cand = []

    for q in QUERIES:
        sr = ac_search(q, pages=1, limit=MAX_SERP, lang="it") or {}
        rows = sr.get("data") or sr.get("results") or []
        for r in rows:
            url = r.get("url")
            title = (r.get("title") or "").strip()
            if not url or not title:
                continue
            if not allowed_url(url):
                continue
            nu = normalize_url(url)
            host = urlparse(nu).netloc
            if nu in seen_urls:
                continue
            if per_host.get(host, 0) >= MAX_PER_HOST:
                continue
            seen_urls.add(nu)
            per_host[host] = per_host.get(host, 0) + 1
            cand.append({"title": title, "url": nu})
        if len(cand) >= MAX_SERP:
            break
    return cand[:MAX_SERP]

def main():
    items = []
    mode = "anycrawl"

    # 1) SERP → candidati ripuliti
    cands = collect_candidates()
    print(f"[SERP] candidati: {len(cands)}")

    # 2) scrape + filtri anti-rumore + scoring
    for c in cands:
        page = ac_scrape(c["url"]) or {}
        txt = text_from_page(page)
        if not good_text(txt):
            continue

        sc = score_text(txt)
        a_type = infer_type(txt)

        why = []
        if "primavera" in txt:          why.append("primavera")
        if "u19" in txt or "under" in txt: why.append("youth")
        if "transfer" in txt or "mercato" in txt or "prestito" in txt: why.append("mercato")
        if "gol" in txt or "assist" in txt: why.append("prestazioni")
        if "esordio" in txt or "debutto" in txt: why.append("esordio")

        items.append({
            "entity": "PLAYER",
            "label": c["title"][:80],
            "anomaly_type": a_type,
            "score": sc,
            "why": sorted(set(why)) or ["segnali testuali"],
            "links": [c["url"]],
        })

    # 3) Se vuoto, fallback (rete di sicurezza)
    if not items:
        mode = "fallback"
        base = "https://github.com/mtornani/OB1-Radar"
        for i in range(1, 11):
            items.append({
                "entity": "PLAYER",
                "label": f"Demo anomaly #{i}",
                "anomaly_type": "NOISE_PULSE",
                "score": max(5, 100 - i*7),
                "why": ["fallback mode (no API response)"],
                "links": [base]
            })

    # 4) Ordina e salva
    items = sorted(items, key=lambda x: x["score"], reverse=True)[:10]
    payload = {
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source": "OB1-AnomalyRadar",
        "mode": mode,
        "items": items
    }
    os.makedirs("output", exist_ok=True)
    with open("output/daily.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[OK] wrote output/daily.json with {len(items)} items (mode={mode})")

if __name__ == "__main__":
    main()
