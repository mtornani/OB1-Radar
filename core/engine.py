"""Daily engine that hunts U20 talent with zero human touch."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List

import requests

from . import analysis, config


class OB1Engine:
    def __init__(self) -> None:
        config.ensure_directories()
        self.cache = self._load_cache()
        self.headers = {"Content-Type": "application/json"}
        if config.ANYCRAWL_API_KEY:
            self.headers["Authorization"] = f"Bearer {config.ANYCRAWL_API_KEY}"

    # ---------------------- public API ----------------------
    def run(self) -> Dict[str, Any]:
        harvested = list(self._harvest_candidates())
        ranked = analysis.rank_candidates(harvested, top_k=config.TOP_K)
        breakdown = Counter(item.get("region", "unknown") for item in ranked)

        payload = {
            "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "items": [self._public_item(item) for item in ranked],
            "region_breakdown": breakdown,
        }
        self._write_output(payload)
        self._save_cache()
        return payload

    # ---------------------- harvest -------------------------
    def _harvest_candidates(self) -> Iterable[Dict[str, Any]]:
        seen_hosts = Counter()
        for query in config.QUERIES:
            search = self._search(query)
            for result in search:
                url = (result.get("url") or "").strip()
                if not url or not analysis.allowed_url(url):
                    continue
                norm = self._normalize_url(url)
                if self._is_seen(norm):
                    continue
                host = analysis.host_from_url(norm)
                region = self._region_for_host(host)
                if region:
                    seen_hosts[region] += 1
                document = self._scrape(norm, host)
                if not document:
                    continue
                record = {
                    "url": norm,
                    "title": result.get("title") or document.get("title"),
                    "text": document.get("text") or document.get("markdown"),
                    "published_at": result.get("published_at") or document.get("published_at"),
                    "region": region or "unknown",
                }
                self._mark_seen(norm, host)
                yield record
            if len(seen_hosts) >= len(config.REGION_MIN_QUOTAS) and all(
                seen_hosts[region] >= quota for region, quota in config.REGION_MIN_QUOTAS.items()
            ):
                continue

    # ---------------------- IO helpers ----------------------
    def _search(self, query: str) -> List[Dict[str, Any]]:
        payload = {"query": query, "pages": 1, "limit": config.MAX_SERP}
        response = self._post("/v1/search", payload)
        items = response.get("items") or response.get("data") or []
        if isinstance(items, dict):
            items = items.get("items", [])
        return items

    def _scrape(self, url: str, host: str) -> Dict[str, Any]:
        engine = config.DOMAIN_ENGINE.get(host, "cheerio")
        payload = {"url": url, "engine": engine, "formats": ["markdown", "text"]}
        response = self._post("/v1/scrape", payload)
        return response.get("data") or response

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{config.ANYCRAWL_API_URL}{path}"
        try:
            res = requests.post(url, headers=self.headers, json=payload, timeout=config.TIMEOUT_S)
            res.raise_for_status()
            data = res.json()
            if not isinstance(data, dict):
                return {}
            return data
        except Exception:
            return {}

    # ---------------------- cache ---------------------------
    def _load_cache(self) -> Dict[str, Any]:
        if not config.CACHE_PATH.exists():
            return {}
        try:
            return json.loads(config.CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_cache(self) -> None:
        config.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        config.CACHE_PATH.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8")

    def _is_seen(self, url: str) -> bool:
        record = self.cache.get(url)
        if not record:
            return False
        try:
            seen_at = datetime.fromisoformat(record["seen_at"])
        except Exception:
            return False
        return datetime.utcnow() - seen_at < timedelta(days=config.CACHE_TTL_DAYS)

    def _mark_seen(self, url: str, host: str) -> None:
        self.cache[url] = {"host": host, "seen_at": datetime.utcnow().isoformat(timespec="seconds")}

    # ---------------------- utils ---------------------------
    @staticmethod
    def _normalize_url(url: str) -> str:
        from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

        parsed = urlparse(url)
        if not parsed.scheme:
            return url
        clean_qs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
        return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path, "", urlencode(sorted(clean_qs)), ""))

    @staticmethod
    def _region_for_host(host: str) -> str:
        for region, hosts in config.SITE_PACKS.items():
            if host in hosts:
                return region
        return "global"

    @staticmethod
    def _public_item(item: Dict[str, Any]) -> Dict[str, Any]:
        clean = dict(item)
        clean.pop("region", None)
        return clean

    def _write_output(self, payload: Dict[str, Any]) -> None:
        config.DAILY_OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        snapshot = config.SNAPSHOT_DIR / f"daily-{payload['generated_at_utc'].replace(':', '').replace('-', '')}.json"
        snapshot.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    engine = OB1Engine()
    engine.run()


if __name__ == "__main__":
    main()
