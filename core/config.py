"""Central configuration for OB1."""
import os
from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
DAILY_OUTPUT = OUTPUT_DIR / "daily.json"

# API Keys (from env)
ANYCRAWL_API_KEY = os.getenv("ANYCRAWL_API_KEY", "")
ANYCRAWL_API_URL = os.getenv("ANYCRAWL_API_URL", "https://api.anycrawl.dev").rstrip("/")
STRIPE_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
TWITTER_KEY = os.getenv("TWITTER_BEARER", "")

# Business Logic
PRICING = {
    "certificate": 49,
    "instant": 9.99,
    "monthly": 89,
    "insider": 999,
}

# Scraping Config
MAX_SERP = 14
MIN_TEXT_LEN = 600
TIMEOUT_S = 50
RECENT_DAYS = 21
CACHE_TTL_DAYS = 14
TOP_K = 10
REGION_MIN_QUOTAS = {"africa": 2, "asia": 3}

# Query packs
SITE_PACKS = {
    "africa": ["cafonline.com", "cosafa.com", "cecafaonline.com", "ufoawafub.com"],
    "asia": [
        "the-afc.com",
        "aseanfootball.org",
        "eaff.com",
        "the-waff.com",
        "saffederation.org",
        "jfa.jp",
        "kfa.or.kr",
        "vff.org.vn",
        "fathailand.org",
        "qfa.qa",
        "the-aiff.com",
        "pssi.org",
    ],
    "south-america": [
        "conmebol.com",
        "ge.globo.com",
        "ole.com.ar",
        "tycsports.com",
        "as.com",
        "marca.com",
        "transfermarkt",
    ],
}

BASE_QUERIES = [
    "Sub 20 debutó fútbol",
    "juvenil Sub 20 goles asistencias",
    "transfer Sub-20 fichaje préstamo juvenil",
    "Sub-20 estreia futebol",
    "base Sub-20 gols assistências",
    "estreou convocado seleção Sub-20",
    "U20 a débuté football",
    "sélection U20 sélectionné football",
    "U20 debut football",
    "U20 transfer loan youth",
]

TOK_JP = ["U-20 日本代表", "U-19 日本代表", "デビュー", "得点", "アシスト", "移籍", "レンタル"]
TOK_KR = ["U-20代表팀", "U-19代表팀", "데뷔", "득점", "도움", "이적", "임대"]
TOK_AR = ["تحت 20", "تحت 19", "منتخب الشباب", "سجل", "صنع", "انتقال", "إعارة", "ظهور"]
TOK_TH = ["ทีมชาติ U20", "ทีมชาติ U19", "เดบิวต์", "ยิง", "แอสซิสต์", "ยืมตัว", "โอนย้าย"]
TOK_VI = ["U20", "U19", "đội tuyển", "ra mắt", "ghi bàn", "kiến tạo", "chuyển nhượng", "cho mượn"]
TOK_ID = ["U20", "U19", "timnas", "debut", "gol", "assist", "pinjaman", "transfer"]

# Pattern weights
POSITIVE_PATTERNS = {
    r"\\bgol\\b|\\bgoal\\b|\\bgoles\\b|\\bgols\\b|\\bbuts\\b": 2.0,
    r"\\bassist\\b|\\bassistenza\\b|\\basistencia\\b|\\bassistências?\\b|\\bpasse(?:s)? décisive(?:s)?\\b": 1.6,
    r"\\bunder\\b|\\bu[\\-\\s]?19\\b|\\bu[\\-\\s]?17\\b|\\bu[\\-\\s]?20\\b|\\bsub[- ]?20\\b|\\bsub[- ]?19\\b|\\bsub[- ]?17\\b|\\bprimavera\\b|\\bjuvenil\\b": 1.3,
    r"\\besordio\\b|\\bdebutto\\b|\\bdebut(?:é|e|o|ou)?\\b|\\bestreia\\b|\\ba débuté\\b|デビュー|데뷔|ظهور|เดบิวต์|ra\\smắt": 2.2,
    r"\\btransfer\\b|\\bmercato\\b|\\bfichaje\\b|\\btraspaso\\b|\\bpr[êe]t\\b|\\bpréstamo\\b|\\bempr[eê]stimo\\b|\\bloan\\b|\\bcedid[oa]\\b|\\bcedut[oa]\\b|\\bsigned\\b|移籍|レンタル|이적|임대|انتقال|إعارة|chuyển nhượng|cho mượn|pinjaman": 1.5,
    r"\\bconvocado\\b|\\bconvocato\\b|\\bselecci[oó]n(?:ado)?\\b|\\bs[eé]lectionn[ée]?\\b|\\bcalled up\\b": 1.4,
    r"\\bnazionale\\b|\\bsele[cç][aã]o\\b|\\bselecci[oó]n\\b|\\bnational team\\b|\\bs[eé]lection\\b": 1.2,
}

MUST_HAVE_PATTERN = (
    r"(f[uú]tbol|futebol|football|soccer|primavera|cantera|juvenil|u[\\-\\s]?20|u[\\-\\s]?19|u[\\-\\s]?17|日本代表|代表|デビュー|得点|アシスト|代表팀|데뷔|득점|منتخب|تحت\\s?20|ظهور|ทีมชาติ|เดบิวต์|đội tuyển|ra mắt|timnas)"
)

NEGATIVE_PATTERNS = (
    "cookie",
    "privacy",
    "accetta",
    "banner",
    "abbonati",
    "paywall",
    "newsletter",
)

BLOCK_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".zip", ".rar")
NEG_URL_PATTERNS = (
    "/rules",
    "/reglas",
    "/regulations",
    "/how-to",
    "/como-",
    "/guia",
    "/guide",
    "/privacy",
    "/cookies",
    "/terminos",
    "/terms",
    "/about",
    "/acerca-",
)
OFF_PATTERNS = (
    "basket",
    "baloncesto",
    "basquete",
    "handball",
    "handebol",
    "voleibol",
    "volei",
    "rugby",
    "/economia",
    "/politica",
    "/motori",
    "almanacco",
    "forumfree",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "wikipedia.org",
)
HOST_BLOCKLIST = {"apwin.com"}
HOST_PENALTY = {"transferfeed.com": 0.6, "olympics.com": 0.85}
TRUST_WEIGHTS = {
    "cafonline.com": 1.20,
    "cosafa.com": 1.15,
    "cecafaonline.com": 1.12,
    "ufoawafub.com": 1.10,
    "the-afc.com": 1.18,
    "aseanfootball.org": 1.10,
    "eaff.com": 1.10,
    "the-waff.com": 1.10,
    "saffederation.org": 1.08,
    "jfa.jp": 1.18,
    "kfa.or.kr": 1.15,
    "vff.org.vn": 1.10,
    "fathailand.org": 1.10,
    "qfa.qa": 1.10,
    "the-aiff.com": 1.10,
    "pssi.org": 1.08,
    "conmebol.com": 1.18,
    "ge.globo.com": 1.18,
    "ole.com.ar": 1.15,
    "tycsports.com": 1.10,
    "as.com": 1.08,
    "marca.com": 1.08,
}
DOMAIN_ENGINE = {
    "kfa.or.kr": "playwright",
    "qfa.qa": "playwright",
    "the-aiff.com": "playwright",
}

NEGATIVE_TERMS = (
    "cookie",
    "privacy",
    "newsletter",
)

CACHE_PATH = DATA_DIR / "cache_seen.json"
SNAPSHOT_DIR = OUTPUT_DIR / "snapshots"

# Utility

def ensure_directories() -> None:
    """Ensure directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def build_site_queries():
    out = []
    for hosts in SITE_PACKS.values():
        for host in hosts:
            out.extend(
                [
                    f"site:{host} U20",
                    f"site:{host} U19",
                    f"site:{host} debut U20",
                    f"site:{host} youth U20",
                ]
            )
    return out


def build_asia_lang_queries():
    out = []
    asia_hosts = SITE_PACKS["asia"]
    for host in asia_hosts:
        for token in TOK_JP + TOK_KR + TOK_AR + TOK_TH + TOK_VI + TOK_ID:
            out.append(f"site:{host} {token}")
    out.extend(
        [
            "U-20 日本代表 デビュー",
            "U-20 代表 得点",
            "U-20 대표팀 데뷔 득점",
            "U-20 대표팀 이적 임대",
            "منتخب الشباب تحت 20 انتقال إعارة",
            "U20 ทีมชาติ เดบิวต์ ยิง",
            "U20 ra mắt ghi bàn kiến tạo chuyển nhượng",
            "U20 timnas debut gol assist transfer",
        ]
    )
    return out


QUERIES = BASE_QUERIES + build_site_queries() + build_asia_lang_queries()
