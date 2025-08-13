#!/usr/bin/env python3
# OB1 • Ouroboros Radar — engine/run.py (v0.4.2.3)
# Add: region_breakdown nel payload + quota Asia=3 (temporanea)
# Include fix recency + query locali Asia

import os, json, re, requests
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

API_URL = os.getenv("ANYCRAWL_API_URL", "https://api.anycrawl.dev").rstrip("/")
API_KEY = os.getenv("ANYCRAWL_API_KEY", "")
HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["Authorization"] = f"Bearer {API_KEY}"

# ---------- packs/queries ----------
SITE_PACKS = {
    "africa": ["cafonline.com","cosafa.com","cecafaonline.com","ufoawafub.com"],
    "asia": [
        "the-afc.com","aseanfootball.org","eaff.com","the-waff.com","saffederation.org",
        "jfa.jp","kfa.or.kr","vff.org.vn","fathailand.org","qfa.qa","the-aiff.com","pssi.org"
    ],
    "south-america": ["conmebol.com","ge.globo.com","ole.com.ar","tycsports.com","as.com","marca.com","transfermarkt"]
}
BASE_QUERIES = [
    "Sub 20 debutó fútbol","juvenil Sub 20 goles asistencias",
    "transfer Sub-20 fichaje préstamo juvenil","Sub-20 estreia futebol",
    "base Sub-20 gols assistências","estreou convocado seleção Sub-20",
    "U20 a débuté football","sélection U20 sélectionné football",
    "U20 debut football","U20 transfer loan youth",
]
TOK_JP = ["U-20 日本代表","U-19 日本代表","デビュー","得点","アシスト","移籍","レンタル"]
TOK_KR = ["U-20代表팀","U-19代表팀","데뷔","득점","도움","이적","임대"]
TOK_AR = ["تحت 20","تحت 19","منتخب الشباب","سجل","صنع","انتقال","إعارة","ظهور"]
TOK_TH = ["ทีมชาติ U20","ทีมชาติ U19","เดบิวต์","ยิง","แอสซิสต์","ยืมตัว","โอนย้าย"]
TOK_VI = ["U20","U19","đội tuyển","ra mắt","ghi bàn","kiến tạo","chuyển nhượng","cho mượn"]
TOK_ID = ["U20","U19","timnas","debut","gol","assist","pinjaman","transfer"]

def build_site_queries():
    out=[]
    for hosts in SITE_PACKS.values():
        for h in hosts:
            out += [f"site:{h} U20", f"site:{h} U19", f"site:{h} debut U20", f"site:{h} youth U20"]
    return out

def build_asia_lang_queries():
    out=[]; asia_hosts=SITE_PACKS["asia"]
    for h in asia_hosts:
        for tok in (TOK_JP+TOK_KR+TOK_AR+TOK_TH+TOK_VI+TOK_ID):
            out.append(f"site:{h} {tok}")
    out += [
        "U-20 日本代表 デビュー","U-20 代表 得点",
        "U-20 대표팀 데뷔 득점","U-20 대표팀 이적 임대",
        "منتخب الشباب تحت 20 انتقال إعارة","U20 ทีมชาติ เดบิวต์ ยิง",
        "U20 ra mắt ghi bàn kiến tạo chuyển nhượng","U20 timnas debut gol assist transfer"
    ]
    return out

QUERIES = BASE_QUERIES + build_site_queries() + build_asia_lang_queries()

# ---------- heuristics ----------
MAX_SERP=14; MIN_TEXT_LEN=600; TIMEOUT_S=50; RECENT_DAYS=21; CACHE_TTL_DAYS=14
REGION_MIN_QUOTAS={"africa":2,"asia":3}   # quota temporanea Asia=3
TOP_K=10

CACHE_PATH="data/cache_seen.json"; OUT_DIR="output"; SNAP_DIR=os.path.join(OUT_DIR,"snapshots")
BLOCK_EXT=(".pdf",".jpg",".jpeg",".png",".gif",".svg",".webp",".zip",".rar")
NEG_URL_PATTERNS=("/rules","/reglas","/regulations","/how-to","/como-","/guia","/guide","/privacy","/cookies","/terminos","/terms","/about","/acerca-")
OFF_PATTERNS=("basket","baloncesto","basquete","handball","handebol","voleibol","volei","rugby","/economia","/politica","/motori","almanacco","forumfree","facebook.com","instagram.com","tiktok.com","wikipedia.org")
HOST_BLOCKLIST={"apwin.com"}; HOST_PENALTY={"transferfeed.com":0.6,"olympics.com":0.85}
TRUST_WEIGHTS={
    "cafonline.com":1.20,"cosafa.com":1.15,"cecafaonline.com":1.12,"ufoawafub.com":1.10,
    "the-afc.com":1.18,"aseanfootball.org":1.10,"eaff.com":1.10,"the-waff.com":1.10,"saffederation.org":1.08,
    "jfa.jp":1.18,"kfa.or.kr":1.15,"vff.org.vn":1.10,"fathailand.org":1.10,"qfa.qa":1.10,"the-aiff.com":1.10,"pssi.org":1.08,
    "conmebol.com":1.18,"ge.globo.com":1.18,"ole.com.ar":1.15,"tycsports.com":1.10,"as.com":1.08,"marca.com":1.08,
}
DOMAIN_ENGINE={"kfa.or.kr":"playwright","qfa.qa":"playwright","the-aiff.com":"playwright"}

POS_WEIGHTS={
    r"\bgol\b|\bgoal\b|\bgoles\b|\bgols\b|\bbuts\b":2.0,
    r"\bassist\b|\bassistenza\b|\basistencia\b|\bassistências?\b|\bpasse(?:s)? décisive(?:s)?\b":1.6,
    r"\bunder\b|\bu[\-\s]?19\b|\bu[\-\s]?17\b|\bu[\-\s]?20\b|\bsub[- ]?20\b|\bsub[- ]?19\b|\bsub[- ]?17\b|\bprimavera\b|\bjuvenil\b":1.3,
    r"\besordio\b|\bdebutto\b|\bdebut(?:é|e|o|ou)?\b|\bestreia\b|\ba débuté\b|デビュー|데뷔|ظهور|เดบิวต์|ra\smắt":2.2,
    r"\btransfer\b|\bmercato\b|\bfichaje\b|\btraspaso\b|\bpr[êe]t\b|\bpréstamo\b|\bempr[eê]stimo\b|\bloan\b|\bcedid[oa]\b|\bcedut[oa]\b|\bsigned\b|移籍|レンタル|이적|임대|انتقال|إعارة|chuyển nhượng|cho mượn|pinjaman":1.5,
    r"\bconvocado\b|\bconvocato\b|\bselecci[oó]n(?:ado)?\b|\bs[eé]lectionn[ée]?\b|\bcalled up\b":1.4,
    r"\bnazionale\b|\bsele[cç][aã]o\b|\bselecci[oó]n\b|\bnational team\b|\bs[eé]lection\b":1.2,
}
MUST_HAVE_REGEX=re.compile(r"(f[uú]tbol|futebol|football|soccer|primavera|cantera|juvenil|u[\-\s]?20|u[\-\s]?19|u[\-\s]?17|日本代表|代表|デビュー|得点|アシスト|대표팀|데뷔|득점|منتخب|تحت\s?20|ظهور|ทีมชาติ|เดบิวต์|đội tuyển|ra mắt|timnas)")
NEG_PATTERNS=("cookie","privacy","accetta","banner","abbonati","paywall","newsletter")
TOURNAMENT_CONFED={"maurice revello":"international","toulon":"international","conmebol":"CONMEBOL","sudamericano":"CONMEBOL","caf u-20":"CAF","u-20 afcon":"CAF","afc u20":"AFC","u20 asian cup":"AFC","concacaf u-20":"CONCACAF"}

# ---------- AnyCrawl ----------
def ac_post(path,payload):
    try:
        r=requests.post(f"{API_URL}{path}",headers=HEADERS,json=payload,timeout=TIMEOUT_S)
        if r.status_code>=400:
            print(f"[AnyCrawl] {path} HTTP {r.status_code} :: {r.text[:200]}"); return None
        return r.json()
    except Exception as e:
        print(f"[AnyCrawl] error {path}: {e}"); return None

def ac_search(query,pages=1,limit=20,lang="all"): return ac_post("/v1/search",{"query":query,"pages":pages,"limit":limit,"lang":lang})
def ac_scrape(url,engine="cheerio"): return ac_post("/v1/scrape",{"url":url,"engine":engine,"formats":["markdown","text"]})

# ---------- cache ----------
def load_cache():
    try:
        with open(CACHE_PATH,"r",encoding="utf-8") as f: return json.load(f)
    except: return {}
def save_cache(cache): os.makedirs(os.path.dirname(CACHE_PATH),exist_ok=True); open(CACHE_PATH,"w",encoding="utf-8").write(json.dumps(cache,ensure_ascii=False,indent=2))
def is_seen(cache,url):
    rec=cache.get(url); 
    if not rec: return False
    try: seen=datetime.fromisoformat(rec["seen_at"])
    except: return False
    return (datetime.utcnow()-seen)<timedelta(days=CACHE_TTL_DAYS)
def mark_seen(cache,url,host): cache[url]={"host":host,"seen_at":datetime.utcnow().isoformat(timespec="seconds")}

# ---------- utils ----------
def normalize_url(u):
    p=urlparse(u)
    if not p.scheme: return u
    q=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith("utm_")]
    return urlunparse((p.scheme,p.netloc.lower(),p.path,"",urlencode(sorted(q)),""))
def allowed_url(u):
    lu=u.lower()
    if any(lu.endswith(ext) for ext in BLOCK_EXT): return False
    if any(tok in lu for tok in OFF_PATTERNS): return False
    if any(tok in lu for tok in NEG_URL_PATTERNS): return False
    host=urlparse(u).netloc.lower()
    if host in HOST_BLOCKLIST: return False
    return True
def text_from_page(scrape_json):
    if not scrape_json: return ""
    data=scrape_json.get("data") or {}
    t=data.get("markdown") or data.get("text") or ""
    return t if isinstance(t,str) else ""

def good_text(txt):
    t=(txt or "").lower()
    if len(t)<MIN_TEXT_LEN: return False
    if not MUST_HAVE_REGEX.search(t): return False
    if sum(t.count(w) for w in NEG_PATTERNS)>20: return False
    hits=0
    for k in ["gol","goal","goles","gols","buts","assist","asistencia","assistência","passe decisiva",
              "primavera","juvenil","u20","u-20","u19","u-19","u17","u-17","under","transfer","mercato","fichaje",
              "traspaso","préstamo","empréstimo","loan","prêt","debut","debutto","esordio","estreia",
              "sélection","selección","nazionale","national team","conmebol","caf","afc","concacaf",
              "デビュー","得点","アシスト","移籍","レンタル","데뷔","득점","도움","이적","임대",
              "منتخب","تحت 20","سجل","صنع","انتقال","إعارة","ظهور","เดบิวต์","ยิง","แอสซิสต์","ยืมตัว","โอนย้าย",
              "ra mắt","ghi bàn","kiến tạo","chuyển nhượng","cho mượn","timnas","pinjaman"]:
        hits+=t.count(k)
    return hits>=2

def score_text(txt):
    t=(txt or "").lower(); score=0.0
    for pat,w in POS_WEIGHTS.items(): score+=w*len(re.findall(pat,t))
    return float(max(0,min(100,round(score,2))))

def infer_type(txt):
    t=(txt or "").lower()
    if re.search(r"\besordio\b|\bdebut(?:é|e|o|ou)?\b|デビュー|데뷔|ظهور|เดบิวต์|ra mắt",t): return "PLAYER_BURST"
    if re.search(r"\btransfer\b|\bmercato\b|\bfichaje\b|\btraspaso\b|\bpr[êe]t\b|\bpréstamo\b|\bempr[eê]stimo\b|\bloan\b|\bcedid[oa]\b|\bcedut[oa]\b|\bsigned\b|移籍|レンタル|이적|임대|انتقال|إعارة|chuyển nhượng|cho mượn|pinjaman",t): return "TRANSFER_SIGNAL"
    return "NOISE_PULSE"

# date inference (robusta)
IT_MONTHS=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
ES_MONTHS=["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
PT_MONTHS=["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
FR_MONTHS=["janvier","février","fevrier","mars","avril","mai","juin","juillet","août","aout","septembre","octobre","novembre","décembre","decembre"]
MONTHS_ALL=IT_MONTHS+ES_MONTHS+PT_MONTHS+FR_MONTHS

def guess_date_from_text_or_url(txt,url):
    t=(txt or "").lower()
    m=re.search(r"/(20\d{2})[\/\-](0[1-9]|1[0-2])[\/\-](0[1-9]|[12]\d|3[01])",url)
    if m:
        y,mm,dd=map(int,m.groups())
        try: return datetime(y,mm,dd)
        except: pass
    m=re.search(r"(20\d{2})[\/\-](0[1-9]|1[0-2])",url)
    if m:
        y,mm=map(int,m.groups())
        try: return datetime(y,mm,1)
        except: pass
    m=re.search(r"(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])",t)
    if m:
        y,mm,dd=map(int,m.groups())
        try: return datetime(y,mm,dd)
        except: pass
    m=re.search(r"\b(0?[1-9]|[12]\d|3[01])[\/\-](0?[1-9]|1[0-2])[\/\-](20\d{2})\b",t)
    if m:
        dd,mm,y=map(int,m.groups())
        try: return datetime(y,mm,dd)
        except: pass
    months="|".join([re.escape(x) for x in MONTHS_ALL])
    m=re.search(r"\b(0?[1-9]|[12]\d|3[01])\s+("+months+r")\s+(20\d{2})\b",t)
    if m:
        dd=int(m.group(1)); name=m.group(2); y=int(m.group(3))
        def idx(name):
            for lst in (IT_MONTHS,ES_MONTHS,PT_MONTHS,FR_MONTHS):
                if name in lst: return lst.index(name)+1
            return 1
        try: return datetime(y,idx(name),dd)
        except: pass
    m=re.search(r"\b(20\d{2})\b",t)
    if m:
        y=int(m.group(1))
        try: return datetime(y,1,1)
        except: pass
    return None

def recency_boost(dt,now=None):
    if not dt: return 0.0
    now=now or datetime.utcnow(); age=(now-dt).days
    if age<0: return 0.0
    if age<=RECENT_DAYS: return round(10.0*(1-age/RECENT_DAYS),2)
    return 0.0

def domain_weight(url):
    host=urlparse(url).netloc.lower()
    if host in HOST_PENALTY: return HOST_PENALTY[host]
    for k,w in TRUST_WEIGHTS.items():
        if k in host: return w
    return 1.0

def region_from_host_or_tld(host):
    h=host.lower()
    if any(dom in h for dom in SITE_PACKS["africa"]): return "africa"
    if any(dom in h for dom in SITE_PACKS["asia"]): return "asia"
    if h.endswith((".za",".ng",".gh",".ma",".tn",".dz",".ke",".ug",".tz",".sn",".cm")): return "africa"
    if h.endswith((".jp",".kr",".id",".th",".vn",".my",".in",".cn",".ph",".sg",".qa",".ae",".sa",".kw",".bh",".om",".jo")): return "asia"
    if h.endswith((".br",".ar",".cl",".uy",".pe",".co",".py",".bo",".ec",".ve")): return "south-america"
    return "unknown"

def infer_confed(txt):
    t=(txt or "").lower()
    for k,conf in TOURNAMENT_CONFED.items():
        if k in t: return conf
    return "unknown"

def preferred_engine_for(host):
    for dom,eng in DOMAIN_ENGINE.items():
        if dom in host.lower(): return eng
    return "cheerio"

def ac_scrape_smart(url):
    host=urlparse(url).netloc
    eng=preferred_engine_for(host)
    js=ac_scrape(url,engine=eng) or {}
    if len(text_from_page(js))<MIN_TEXT_LEN and eng!="playwright":
        js2=ac_scrape(url,engine="playwright")
        return (js2 or js),"playwright" if js2 else eng
    return js,eng

# ---------- pipeline ----------
def collect_candidates(cache):
    seen,per_host,cand=set(),{},[]
    for q in QUERIES:
        sr=ac_search(q,pages=1,limit=MAX_SERP,lang="all") or {}
        rows=sr.get("data") or sr.get("results") or []
        for r in rows:
            url=r.get("url"); title=(r.get("title") or "").strip()
            if not url or not title: continue
            if not allowed_url(url):  continue
            nu=normalize_url(url); host=urlparse(nu).netloc.lower()
            if nu in seen or is_seen(cache,nu): continue
            cap=1 if (host in HOST_PENALTY or host in HOST_BLOCKLIST) else 2
            if per_host.get(host,0)>=cap: continue
            seen.add(nu); per_host[host]=per_host.get(host,0)+1
            cand.append({"title":title,"url":nu})
        if len(cand)>=MAX_SERP: break
    return cand[:MAX_SERP]

def select_with_region_quotas(items,k=TOP_K,quotas=REGION_MIN_QUOTAS):
    picked,used=[],set()
    for region,q in quotas.items():
        pool=[it for it in items if region in it.get("why",[])]
        pool.sort(key=lambda x:x.get("score",0),reverse=True)
        for it in pool[:q]:
            key=tuple(it.get("links",[]))
            if key in used: continue
            picked.append(it); used.add(key)
    rest=[it for it in items if tuple(it.get("links",[])) not in used]
    rest.sort(key=lambda x:x.get("score",0),reverse=True)
    for it in rest:
        if len(picked)>=k: break
        picked.append(it)
    return picked[:k]

def region_breakdown(items):
    b={"africa":0,"asia":0,"south-america":0,"international":0,"unknown":0}
    for it in items:
        tags = it.get("why",[])
        for r in ("africa","asia","south-america","international"):
            if r in tags:
                b[r]+=1
                break
        else:
            b["unknown"]+=1
    return b

def main():
    cache=load_cache()
    cands=collect_candidates(cache)
    print(f"[SERP] candidati: {len(cands)}")

    items=[]
    for c in cands:
        page,used_engine=ac_scrape_smart(c["url"])
        txt=text_from_page(page)
        if not good_text(txt): continue

        sc=score_text(txt)
        a_type=infer_type(txt)
        dt=guess_date_from_text_or_url(txt,c["url"])
        sc+=recency_boost(dt)
        sc=float(max(0,min(100,round(sc*domain_weight(c["url"]),2))))

        host=urlparse(c["url"]).netloc.lower()
        region=region_from_host_or_tld(host)
        conf=infer_confed(txt)
        if conf=="international": region="international"

        why=[]
        if any(k in txt for k in ["primavera","juvenil","ユース","유스","đội trẻ","เยาวชน"]): why.append("youth")
        if any(k in txt for k in ["transfer","mercato","fichaje","traspaso","préstamo","empréstimo","loan","prêt","signed","移籍","レンタル","이적","임대","chuyển nhượng","cho mượn","pinjaman"]): why.append("mercato")
        if any(k in txt for k in ["gol","goal","goles","gols","buts","assist","asistencia","assistência","passe decisiva","得点","アシスト","득점","도움","ghi bàn","kiến tạo","ยิง","แอสซิสต์"]): why.append("prestazioni")
        if re.search(r"\besordio\b|\bdebut(?:é|e|o|ou)?\b|デビュー|데뷔|ظهور|เดบิวต์|ra mắt",txt): why.append("esordio")
        if dt and (datetime.utcnow()-dt).days<=RECENT_DAYS: why.append("recente")
        if used_engine=="playwright": why.append("js-heavy")
        if conf!="unknown": why.append(conf)
        if region!="unknown": why.append(region)

        items.append({
            "entity":"PLAYER","label":c["title"][:80],"anomaly_type":a_type,"score":sc,
            "why":sorted(set(why)) or ["segnali"],"links":[c["url"]]
        })

        mark_seen(cache,c["url"],host)

    items.sort(key=lambda x:x["score"],reverse=True)
    items=select_with_region_quotas(items,k=TOP_K,quotas=REGION_MIN_QUOTAS)

    payload={
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds")+"Z",
        "source":"OB1-AnomalyRadar","mode":"anycrawl" if items else "fallback",
        "region_breakdown": region_breakdown(items),
        "items": items or [{"entity":"PLAYER","label":"Demo anomaly","anomaly_type":"NOISE_PULSE","score":10,"why":["fallback"],"links":["https://github.com/mtornani/OB1-Radar"]}]
    }

    os.makedirs(OUT_DIR,exist_ok=True); os.makedirs(SNAP_DIR,exist_ok=True)
    open(os.path.join(OUT_DIR,"daily.json"),"w",encoding="utf-8").write(json.dumps(payload,ensure_ascii=False,indent=2))
    today=datetime.utcnow().strftime("%Y-%m-%d")
    open(os.path.join(SNAP_DIR,f"daily-{today}.json"),"w",encoding="utf-8").write(json.dumps(payload,ensure_ascii=False,indent=2))
    save_cache(cache)
    print(f"[OK] wrote output/daily.json (items={len(items)}) – quotas={REGION_MIN_QUOTAS} breakdown={payload['region_breakdown']}")
if __name__=="__main__":
    main()
