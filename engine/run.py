#!/usr/bin/env python3
# OB1 • Ouroboros Radar — engine/run.py (v0.4-fix1)
# AnyCrawl /v1/search + /v1/scrape → filtri → scoring → Top-10
# Novità v0.4: micro-cache URL (14gg), snapshot giornalieri, confederation tags,
# site-packs CAF/AFC rinforzati, block/penalty per aggregatori, fix Maurice Revello
# Fix1: chiusura f-string finale + bug in region_from_host_or_tld

import os, json, re, requests, glob
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# ---- Config -----------------------------------------------------------------
API_URL = os.getenv("ANYCRAWL_API_URL", "https://api.anycrawl.dev").rstrip("/")
API_KEY = os.getenv("ANYCRAWL_API_KEY", "")

HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["Authorization"] = f"Bearer {API_KEY}"

# ---- Site packs (forza copertura AF/AS) -------------------------------------
SITE_PACKS = {
    "africa": [
        "cafonline.com", "cosafa.com", "cecafaonline.com", "ufoawafub.com"
    ],
    "asia": [
        "the-afc.com", "aseanfootball.org"
    ],
    "south-america": [
        "conmebol.com", "ge.globo.com", "ole.com.ar", "tycsports.com", "as.com", "marca.com",
        "transfermarkt"  # wildcard: vari TLD
    ],
}

BASE_QUERIES = [
    # ES/PT (Sudamerica)
    "Sub 20 debutó fútbol", "juvenil Sub 20 goles asistencias",
    "transfer Sub-20 fichaje préstamo juvenil",
    "Sub-20 estreia futebol", "base Sub-20 gols assistências",
    "estreou convocado seleção Sub-20",
    # FR/EN (Africa + Asia EN-first)
    "U20 a débuté football", "sélection U20 sélectionné football",
    "U20 debut football", "U20 transfer loan youth",
]

def build_site_queries():
    out = []
    for hosts in SITE_PACKS.values():
        for h in hosts:
            out += [f"site:{h} U20", f"site:{h} U19", f"site:{h} debut U20", f"site:{h} youth U20"]
    return out

QUERIES = BASE_QUERIES + build_site_queries()

# ---- Heuristics & scoring ---------------------------------------------------
MAX_SERP       = 14
MAX_PER_HOST   = 2
MIN_TEXT_LEN   = 600
TIMEOUT_S      = 50
RECENT_DAYS    = 21
CACHE_TTL_DAYS = 14

# Persistenza cache & snapshot
CACHE_PATH     = "data/cache_seen.json"
OUT_DIR        = "output"
SNAP_DIR       = os.path.join(OUT_DIR, "snapshots")

# Blocchi/penalty
BLOCK_EXT = (".pdf",".jpg",".jpeg",".png",".gif",".svg",".webp",".zip",".rar")
NEG_URL_PATTERNS = (
    "/rules", "/reglas", "/regulations", "/how-to", "/como-", "/guia", "/guide",
    "/privacy", "/cookies", "/terminos", "/terms", "/about", "/acerca-",
)
OFF_PATTERNS = (
    "basket","baloncesto","basquete","handball","handebol","voleibol","volei","rugby",
    "/economia","/politica","/motori","almanacco","forumfree",
    "facebook.com","instagram.com","tiktok.com","wikipedia.org",
)
HOST_BLOCKLIST = {
    "apwin.com",
}
HOST_PENALTY = {
    "transferfeed.com": 0.6,
    "olympics.com": 0.85,
}

TRUST_WEIGHTS = {
    # Africa
    "cafonline.com": 1.20, "cosafa.com": 1.15, "cecafaonline.com": 1.12, "ufoawafub.com": 1.10,
    # Asia
    "the-afc.com": 1.18, "aseanfootball.org": 1.10,
    # Sudamerica
    "conmebol.com": 1.18, "ge.globo.com": 1.18, "ole.com.ar": 1.15, "tycsports.com": 1.10,
    "as.com": 1.08, "marca.com": 1.08,
}

POS_WEIGHTS = {
    r"\bgol\b|\bgoal\b|\bgoles\b|\bgols\b|\bbuts\b": 2.0,
    r"\bassist\b|\bassistenza\b|\basistencia\b|\bassistências?\b|\bpasse(?:s)? décisive(?:s)?\b": 1.6,
    r"\bunder\b|\bu19\b|\bu17\b|\bsub[- ]?20\b|\bsub[- ]?19\b|\bsub[- ]?17\b|\bprimavera\b|\bjuvenil\b": 1.3,
    r"\besordio\b|\bdebutto\b|\bdebut(?:é|e|o|ou)?\b|\bestreia\b|\ba débuté\b": 2.2,
    r"\btransfer\b|\bmercato\b|\bfichaje\b|\btraspaso\b|\bpr[êe]t\b|\bpréstamo\b|\bempr[eê]stimo\b|\bloan\b|\bcedid[oa]\b|\bcedut[oa]\b|\bsigned\b": 1.5,
    r"\bconvocado\b|\bconvocato\b|\bselecci[oó]n(?:ado)?\b|\bs[eé]lectionn[ée]?\b|\bcalled up\b": 1.4,
    r"\bnazionale\b|\bsele[cç][aã]o\b|\bselecci[oó]n\b|\bnational team\b|\bs[eé]lection\b": 1.2,
}

MUST_HAVE_ANY = ("fútbol","futebol","football","soccer","primavera","cantera","juvenil","u20","u19","u17")
NEG_PATTERNS  = ("cookie","privacy","accetta","banner","abbonati","paywall","newsletter")

IT_MONTHS = ["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
ES_MONTHS = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
PT_MONTHS = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
FR_MONTHS = ["janvier","février","fevrier","mars","avril","mai","juin","juillet","août","aout","septembre","octobre","novembre","décembre","decembre"]
MONTHS_ALL  = IT_MONTHS + ES_MONTHS + PT_MONTHS + FR_MONTHS

TOURNAMENT_CONFED = {
    "maurice revello": "international", "toulon": "international",
    "conmebol": "CONMEBOL", "sudamericano": "CONMEBOL",
    "caf u-20": "CAF", "u-20 afcon": "CAF", "afcon u-20": "CAF",
    "afc u20": "AFC", "u20 asian cup": "AFC",
    "concacaf u-20": "CONCACAF"
}

# ---- AnyCrawl client --------------------------------------------------------
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

# ---- Cache (14 giorni) ------------------------------------------------------
def load_cache():
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_cache(cache: dict):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def is_seen(cache, url):
    rec = cache.get(url)
    if not rec: return False
    try:
        seen = datetime.fromisoformat(rec["seen_at"])
    except Exception:
        return False
    return (datetime.utcnow() - seen) < timedelta(days=CACHE_TTL_DAYS)

def mark_seen(cache, url, host):
    cache[url] = {"host": host, "seen_at": datetime.utcnow().isoformat(timespec="seconds")}

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
    if any(tok in lu for tok in NEG_URL_PATTERNS): return False
    host = urlparse(u).netloc.lower()
    if host in HOST_BLOCKLIST: return False
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
        "sélection","selección","seleçao","seleção","national team","nazionale","conmebol","caf","afc","concacaf"
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
    if age <= RECENT_DAYS: return round(10.0 * (1 - age/RECENT_DAYS), 2)
    return 0.0

def domain_weight(url: str):
    host = urlparse(url).netloc.lower()
    if host in HOST_PENALTY: return HOST_PENALTY[host]
    for k, w in TRUST_WEIGHTS.items():
        if k in host: return w
    return 1.0

def host_cap(host: str) -> int:
    if host in HOST_PENALTY or host in HOST_BLOCKLIST: return 1
    return MAX_PER_HOST

def infer_confed(txt: str) -> str:
    t = (txt or "").lower()
    for k, conf in TOURNAMENT_CONFED.items():
        if k in t:
            return conf
    return "unknown"

def region_from_host_or_tld(host: str) -> str:
    h = host.lower()
    if any(dom in h for dom in SITE_PACKS["africa"]): return "africa"
    if any(dom in h for dom in SITE_PACKS["asia"]): return "asia"
    if h.endswith((".za",".ng",".gh",".ma",".tn",".dz",".ke",".ug",".tz",".sn",".cm")): return "africa"
    if h.endswith((".jp",".kr",".id",".th",".vn",".my",".in",".cn",".ph",".sg")): return "asia"
    if h.endswith((".br",".ar",".cl",".uy",".pe",".co",".py",".bo",".ec",".ve")): return "south-america"
    return "unknown"

def retry_scrape_if_thin(url: str, first_json: dict, min_len=MIN_TEXT_LEN):
    txt = text_from_page(first_json)
    if len((txt or "")) >= min_len: return first_json, "cheerio"
    j2 = ac_scrape(url, engine="playwright")
    return (j2 or first_json), ("playwright" if j2 else "cheerio")

# ---- Pipeline ----------------------------------------------------------------
def collect_candidates(cache):
    seen_urls, per_host, cand = set(), {}, []
    for q in QUERIES:
        sr = ac_search(q, pages=1, limit=MAX_SERP, lang="all") or {}
        rows = sr.get("data") or sr.get("results") or []
        for r in rows:
            url = r.get("url"); title = (r.get("title") or "").strip()
            if not url or not title: continue
            if not allowed_url(url):  continue
            nu = normalize_url(url); host = urlparse(nu).netloc.lower()
            if nu in seen_urls:       continue
            if is_seen(cache, nu):    continue
            cap = host_cap(host)
            if per_host.get(host,0) >= cap: continue
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
    cache = load_cache()
    items, mode = [], "anycrawl"

    cands = collect_candidates(cache)
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

        conf = infer_confed(txt)
        host = urlparse(c["url"]).netloc.lower()
        region = region_from_host_or_tld(host)
        if conf == "international":
            region = "international"

        why = []
        if "primavera" in txt: why.append("primavera")
        if any(k in txt for k in ["u20","u19","under","juvenil"]): why.append("youth")
        if any(k in txt for k in ["transfer","mercato","fichaje","traspaso","préstamo","empréstimo","loan","prêt","signed","cedido","ceduta","ceduto"]): why.append("mercato")
        if any(k in txt for k in ["gol","goal","goles","gols","buts","assist","asistencia","assistência","passe decisiva"]): why.append("prestazioni")
        if re.search(r"\besordio\b|\bdebut(?:é|e|o|ou)?\b", txt): why.append("esordio")
        if dt: why.append("recente")
        if used_engine == "playwright": why.append("js-heavy")
        if conf != "unknown": why.append(conf)
        if region != "unknown": why.append(region)

        items.append({
            "entity":"PLAYER",
            "label": c["title"][:80],
            "anomaly_type": a_type,
            "score": sc,
            "why": sorted(set(why)) or ["segnali testuali"],
            "links": [c["url"]],
        })

        mark_seen(cache, c["url"], host)

    if not items:
        mode = "fallback"
        items = fallback_items()

    items = sorted(items, key=lambda x: x["score"], reverse=True)[:10]

    now_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    payload = {
        "generated_at_utc": now_iso,
        "source": "OB1-AnomalyRadar",
        "mode": mode,
        "items": items
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(SNAP_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "daily.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    snap_path = os.path.join(SNAP_DIR, f"daily-{today}.json")
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    save_cache(cache)

    # ✅ f-string chiusa correttamente (era la causa del failure)
    print(f"[OK] wrote {OUT_DIR}/daily.json and snapshot {snap_path} (items={len(items)}, mode={mode})")

if __name__ == "__main__":
    main()
