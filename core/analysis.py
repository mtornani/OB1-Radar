"""Scoring and filtering logic for OB1."""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, Iterable, List

from . import config


MUST_HAVE_REGEX = re.compile(config.MUST_HAVE_PATTERN, re.IGNORECASE)
POSITIVE_REGEXES = [(re.compile(pattern, re.IGNORECASE), weight) for pattern, weight in config.POSITIVE_PATTERNS.items()]


def allowed_url(url: str) -> bool:
    lowered = url.lower()
    if any(lowered.endswith(ext) for ext in config.BLOCK_EXT):
        return False
    if any(token in lowered for token in config.OFF_PATTERNS):
        return False
    if any(token in lowered for token in config.NEG_URL_PATTERNS):
        return False
    host = _host_from_url(lowered)
    if host in config.HOST_BLOCKLIST:
        return False
    return True


def good_text(text: str) -> bool:
    if not text or len(text) < config.MIN_TEXT_LEN:
        return False
    lowered = text.lower()
    if not MUST_HAVE_REGEX.search(lowered):
        return False
    if sum(lowered.count(token) for token in config.NEGATIVE_PATTERNS) > 20:
        return False
    return True


def score_text(text: str) -> float:
    if not text:
        return 0.0
    lowered = text.lower()
    score = 0.0
    for regex, weight in POSITIVE_REGEXES:
        score += weight * len(regex.findall(lowered))
    return float(max(0, min(100, round(score, 2))))


def adjust_for_host(score: float, host: str) -> float:
    if not host:
        return score
    penalty = config.HOST_PENALTY.get(host, 1.0)
    trust = config.TRUST_WEIGHTS.get(host, 1.0)
    return max(0.0, min(100.0, round(score * penalty * trust, 2)))


def extract_signals(text: str, limit: int = 5) -> List[str]:
    if not text:
        return []
    lowered = text.lower()
    keywords = [
        "goal",
        "assist",
        "transfer",
        "debut",
        "penalty",
        "selection",
        "loan",
        "hat-trick",
        "u20",
        "u19",
        "international",
    ]
    counts = Counter()
    for word in keywords:
        if word in lowered:
            counts[word] = lowered.count(word)
    return [word for word, _ in counts.most_common(limit)]


def build_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a crawl document into the public schema."""
    text = raw.get("text", "")
    if not good_text(text):
        raise ValueError("text rejected by heuristics")

    url = raw.get("url", "")
    host = _host_from_url(url)
    base_score = score_text(text)
    adjusted = adjust_for_host(base_score, host)

    return {
        "label": raw.get("title") or raw.get("label") or host,
        "url": url,
        "host": host,
        "score": adjusted,
        "why": extract_signals(text),
        "published_at": raw.get("published_at") or datetime.utcnow().isoformat(timespec="seconds"),
    }


def host_from_url(url: str) -> str:
    """Public helper to extract host names."""
    return _host_from_url(url)


def _host_from_url(url: str) -> str:
    from urllib.parse import urlparse

    try:
        return urlparse(url).netloc.lower()
    except ValueError:
        return ""


def rank_candidates(candidates: Iterable[Dict[str, Any]], top_k: int = config.TOP_K) -> List[Dict[str, Any]]:
    accepted = []
    for candidate in candidates:
        try:
            item = build_item(candidate)
        except ValueError:
            continue
        accepted.append(item)
    accepted.sort(key=lambda item: item["score"], reverse=True)
    return accepted[:top_k]
