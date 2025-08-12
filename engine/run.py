#!/usr/bin/env python3
# OB1 • Ouroboros Radar — engine/run.py (v0.3.1)
# Hot-fix: site-packs Africa/Asia, trust-weight regionale e tag regione in output.

import os, json, re, requests
from datetime import datetime
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

API_URL = os.getenv("ANYCRAWL_API_URL", "https://api.anycrawl.dev").rstrip("/")
API_KEY = os.getenv("ANYCRAWL_API_KEY", "")
HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["Authorization"] = f"Bearer {API_KEY}"

# ---- Site packs per spingere Africa/Asia ------------------------------------
SITE_PACKS = {
    "africa": [
        "cafonline.com",       # CAF U-20 AFCON
        "cosafa.com",          # Africa australe U-20
        "cecafaonline.com",    # Africa est/centro U-20
        "ufoawafub.com",       # WAFU (Africa ovest) U-20
    ],
    "asia": [
        "the-afc.com",         # AFC U-20 Asian Cup
        "aseanfootball.org",   # AFF U18/U19 (SEA)
    ],
    # Sudamerica rimane naturale (molte fonti già emergono senza site:)
    "south-america": [
        "ge.globo.com", "ole.com.ar", "tycsports.com", "as.com", "marca.com",
    ],
}

# Query base multi-lingua (ES/PT/FR/EN) – restano quelle già efficaci
BASE_QUERIES = [
    "Sub 20 debutó fútbol",                    # ES
    "juvenil Sub 20 goles asistencias",        # ES
    "transfer Sub-20 fichaje préstamo juvenil",# ES
    "Sub-20 estreia futebol",                  # PT
    "base Sub-20 gols assistências",           # PT
    "estreou convocado seleção Sub-20",        # PT
    "U20 a débuté football",                   # FR
    "sélection U20 sélectionné",               # FR
    "U20 debut football",                      # EN
    "U20 transfer loan youth",                 # EN
]

# Da site-packs costruiamo query mirate semplici (site: + U20)
def build_site_queries():
    out = []
    for region, hosts in SITE_PACKS.items():
        for h in hosts:
            out += [
                f"site:{h} U20",
                f"site:{h} U19",
                f"site:{h} youth U20",
                f"site:{h} debut U20",
            ]
    return out

QUERIES = BASE_QUERIES + build_site_queries()

MAX_SERP = 14
MAX_PER_HOST = 2
MIN_TEXT_LEN = 600
TIMEOUT_S = 50

BLOCK_EXT = (".pdf",".jpg",".jpeg",".png",".gif",".svg",".webp",".zip",".rar")
OFF_PATTERNS = (
    "basket","baloncesto","basquete","handball","handebol","voleibol","volei","rugby",
    "/economia","/politica","/motori","almanacco","forumfree",
    "facebook.com","instagram.com","tiktok.com","wikipedia.org",
)

POS_WEIGHTS = {
    r"\bgol\b|\bgoal\b|\bgoles\b|\bgols\b|\bbuts\b": 2.0,
    r"\bassist\b|\bassistenza\b|\basistencia\b|\bassistências?\b|\bpasse(?:s)? décisive(?:s)?\b": 1.6,
    r"\bunder\b|\bu19\b|\bu17\b|\bsub[- ]?20\b|\bsub[- ]?19\b|\bsub[- ]?17\b|\bprimavera\b|\bjuvenil\b": 1.3,
    r"\besordio\b|\bdebutto\b|\bdebut(?:é|e|o|ou)?\b|\bestreia\b|\ba débuté\b": 2.2,
    r"\btransfer\b|\bmercato\b|\bfichaje\b|\btraspaso\b|\bpr[êe]t\b|\bpréstamo\b|\bempr[eê]stimo\b|\bloan\b|\bcedid[oa]\b|\bcedut[oa]\b|\bsigned\b": 1.5,
    r"\bconvocado\b|\bconvocato\b|\bselecci[oó]n(?:ado)?\b|\bs[eé]lectionn[ée]?\b|\bcalled up\b": 1.4,
    r"\bnazionale\b|\bsele[cç][aã]o\b|\bselecci[oó]n\b|\bnational team\b|\bs[eé]lection\b": 1.2,
}

MUST_HAVE_ANY = (
    "fútbol","futebol","football","soccer","primavera","cantera","juvenil","u20","u19","u17"
)

RECENT_DAYS = 21
TRUST_WEIGHTS = {
    # Africa
    "cafonline.com": 1.20, "cosafa.com": 1.15, "cecafaonline.com": 1.12, "ufoawafub.com": 1.10,
    # Asia
    "the-afc.com": 1.18, "aseanfootball.org": 1.10,
    # Sudamerica (già presenti)
    "ge.globo.com": 1.18, "ole.com.ar": 1.15, "tycsports.com": 1.10, "as.com": 1.08, "marca.com": 1.08,
}

NEG_PATTERNS = ("cookie","privacy","accetta","banner","abbonati","paywall","newsletter")

IT_MONTHS = ["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
ES_MONTHS = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
PT_MONTHS = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
FR_MONTHS = ["janvier","février","fevrier","mars","avril","mai","juin","juillet","août","aout","septembre","octobre","novembre","décembre","decembre"]
MONTHS_ALL = IT_MONTHS + ES_MONTHS + PT_MONTHS + FR_MONTHS

# ---- AnyCrawl ---------------------------------------------------------------
def ac_post(path: str, payload: dict):
    try:
        r = requests.post(f"{API_URL}{path}", headers=HEADERS, json=payload, timeout=TIMEOUT_S)
        if r.status_code >= 400:
            print(f"[AnyCrawl] {path} HTTP {r.status_code} :: {r.text[:200]}")
            return None
        return r.json()
    except Exception as e:
        print(f"[AnyCrawl] error {path}: {e}")
        return None

def ac_search(query: str, pages: int = 1, limit: int = 20, lang: str = "all"):
    return ac_post("/v1/search", {"query": query, "pages": pages, "limit": limit, "lang": lang})

def ac_scrape(url: str, engine: str = "cheerio"):
    return ac_post("/v1/scrape", {"url": url, "engine": engine, "formats": ["markdown","text"]})

# ---- Utils ------------------------------------------------------------------
def normalize_url(u: str) -> str:
    p = urlparse(u)
    if not p.scheme: return u
    q = [(k,v) for k,v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    return urlunparse((p.scheme, p.netloc.lower(), p.path, "", urlencode(sorted(q)), ""))

def allowed_url(u: str) -> bool:
    lu = u.lower()
    if any(lu.endswith(ext) for ext in BLOCK_EXT): return False
    if any(tok in lu for tok in OFF_PATTERNS):    return False
    return True

def text_from_page(scrape_json: dict) -> str:
    if not scrape_json: return ""
    data = scrape_json.get("data") or {}
    t = data.get("markdown") or data.get("text") or ""
    return t if isinstance(t, str) else ""

def good_text(txt: str) -> bool:
    t = (txt or "").lower()
    if len(t) < MIN_TEXT_LEN: return False
    if not any(k in t for k in MUST_HAVE_ANY): return False
    if sum(t.count(w) for w in NEG_PATTERNS) > 20: return False
    hits = sum(t.count(k) for k in [
        "gol","goal","goles","gols","buts","assist","asistencia","assistência","passe decisiva",
        "primavera","juvenil","u20","u19","u17","under","transfer","mercato","fichaje",
        "traspaso","préstamo","empréstimo","loan","prêt","debut","debutto","esordio","estreia",
        "sélection","selección","seleçao","seleção","national team","nazionale"
    ])
    return hits >= 2

def score_text(txt: str) -> float:
    t = (txt or "").lower()
    score = 0.0
    for pat, w in POS_WEIGHTS.items():
        score += w * len(re.findall(pat, t))
    return float(max(0, min(100, round(score, 2))))

def infer_type(txt: str) -> str:
    t = (txt or "").lower()
    if re.search(r"\besordio\b|\bdebut(?:é|e|o|ou)?\b", t): return "PLAYER_BURST"
    if re.search(r"\btransfer\b|\bmercato\b|\bfichaje\b|\btraspaso\b|\bpr[êe]t\b|\bpréstamo\b|\bempr[eê]stimo\b|\bloan\b|\bcedid[oa]\b|\bcedut[oa]\b|\bsigned\b", t):
        return "TRANSFER_SIGNAL"
    return "NOISE_PULSE"

def guess_date_from_text_or_url(txt: str, url: str):
    t = (txt or "").lower()
    m = re.search(r"/(20\d{2})/(0[1-9]|1[0-2])/", url)
    if m:
        y, mm = int(m.group(1)), int(m.group(2))
        try: return datetime(y, mm, 1)
        except: pass
    months = "|".join([re.escape(x) for x in MONTHS_ALL])
    m2 = re.search(r"(\d{1,2})\s+(" + months + r")\s+(20\d{2})", t)
    if m2:
        d = int(m2.group(1)); month_name = m2.group(2); y = int(m2.group(3))
        def idx(name):
            for lst in (IT_MONTHS, ES_MONTHS, PT_MONTHS, FR_MONTHS):
                if name in lst: return lst.index(name) + 1
            return 1
        try: return datetime(y, idx(month_name), d)
        except: pass
    m3 = re.search(r"(20\d{2})", t)
    if m3:
        y = int(m3.group(1))
        try: return datetime(y,1,1)
        except: pass
    return None

def recency_boost(dt: datetime, now=None):
    if not dt: return 0.0
    now = now or datetime.utcnow()
    age = (now - dt).days
    if age < 0: return 0.0
    if age <= 21: return round(10.0 * (1 - age/21), 2)
    return 0.0

def domain_weight(url: str):
    host = urlparse(url).netloc.lower()
    for k, w in TRUST_WEIGHTS.items():
        if k in host: return w
    return 1.0

def host_region(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if any(h in host for h in SITE_PACKS["africa"]): return "africa"
    if any(h in host for h in SITE_PACKS["asia"]): return "asia"
    # tld heuristic
    if host.endswith((".za",".ng",".gh",".ma",".tn",".dz",".ke",".ug",".tz",".sn",".cm")): return "africa"
    if host.endswith((".jp",".kr",".id",".th",".vn",".my",".in",".cn",".ph",".sg")): return "asia"
    if host.endswith((".br",".ar",".cl",".uy",".pe",".co",".py",".bo",".ec",".ve")): return "south-america"
    return "unknown"

def retry_scrape_if_thin(url: str, first_json: dict, min_len=MIN_TEXT_LEN):
    txt = text_from_page(first_json)
    if len((txt or "")) >= min_len: return first_json, "cheerio"
    j2 = ac_scrape(url, engine="playwright")
    return (j2 or first_json), ("playwright" if j2 else "cheerio")

# ---- Pipeline ----------------------------------------------------------------
def collect_candidates():
    seen_urls, per_host, cand = set(), {}, []
    for q in QUERIES:
        sr = ac_search(q, pages=1, limit=MAX_SERP, lang="all") or {}
        rows = sr.get("data") or sr.get("results") or []
        for r in rows:
            url = r.get("url"); title = (r.get("title") or "").strip()
            if not url or not title: continue
            if not allowed_url(url):  continue
            nu = normalize_url(url); host = urlparse(nu).netloc
            if nu in seen_urls:       continue
            if per_host.get(host,0) >= MAX_PER_HOST: continue
            seen_urls.add(nu); per_host[host] = per_host.get(host,0)+1
            cand.append({"title": title, "url": nu})
        if len(cand) >= MAX_SERP: break
    return cand[:MAX_SERP]

def fallback_items():
    base = "https://github.com/mtornani/OB1-Radar"
    return [{
        "entity":"PLAYER","label":f"Demo anomaly #{i}","anomaly_type":"NOISE_PULSE",
        "score":max(5,100-i*7),"why":["fallback mode (no API response)"],"links":[base]
    } for i in range(1,11)]

def main():
    items, mode = [], "anycrawl"
    cands = collect_candidates()
    print(f"[SERP] candidati: {len(cands)}")

    for c in cands:
        first = ac_scrape(c["url"], engine="cheerio") or {}
        page, used_engine = retry_scrape_if_thin(c["url"], first, min_len=MIN_TEXT_LEN)
        txt = text_from_page(page)
        if not good_text(txt): continue

        sc = score_text(txt)
        a_type = infer_type(txt)
        dt = guess_date_from_text_or_url(txt, c["url"])
        sc += recency_boost(dt)
        sc = round(sc * domain_weight(c["url"]), 2)
        sc = float(max(0, min(100, sc)))

        region = host_region(c["url"])
        why = []
        if "primavera" in txt: why.append("primavera")
        if any(k in txt for k in ["u20","u19","under","juvenil"]): why.append("youth")
        if any(k in txt for k in ["transfer","mercato","fichaje","traspaso","préstamo","empréstimo","loan","prêt","signed","cedido","ceduta","ceduto"]): why.append("mercato")
        if any(k in txt for k in ["gol","goal","goles","gols","buts","assist","asistencia","assistência","passe decisiva"]): why.append("prestazioni")
        if re.search(r"\besordio\b|\bdebut(?:é|e|o|ou)?\b", txt): why.append("esordio")
        if dt: why.append("recente")
        if used_engine == "playwright": why.append("js-heavy")
        if region != "unknown": why.append(region)

        items.append({
            "entity":"PLAYER",
            "label": c["title"][:80],
            "anomaly_type": a_type,
            "score": sc,
            "why": sorted(set(why)) or ["segnali testuali"],
            "links": [c["url"]],
        })

    if not items:
        mode = "fallback"
        items = fallback_items()

    items = sorted(items, key=lambda x: x["score"], reverse=True)[:10]
    payload = {
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source": "OB1-AnomalyRadar",
        "mode": mode,
        "items": items
    }
    os.makedirs("output", exist_ok=True)
    with open("output/daily.json","w",encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[OK] wrote output/daily.json with {len(items)} items (mode={mode})")

if __name__ == "__main__":
    main()
