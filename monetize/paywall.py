"""Payment tiers and paywall slicing logic."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict

from core import config


class OB1Paywall:
    """Serve radar output according to the brutal tier structure."""

    def __init__(self) -> None:
        self.data_path = config.DAILY_OUTPUT
        self.tiers: Dict[str, Dict[str, float]] = {
            "free": {"delay_hours": 48, "players": 3, "price": 0},
            "instant": {"delay_hours": 0, "players": 1, "price": config.PRICING["instant"]},
            "pro": {"delay_hours": 0, "players": 10, "price": config.PRICING["monthly"], "monthly": True},
            "insider": {
                "delay_hours": -24,
                "players": 999,
                "price": config.PRICING["insider"],
                "monthly": True,
            },
        }

    # ---------------------- public API ----------------------
    def generate_teaser(self) -> Dict[str, object]:
        data = self._load_latest()
        items = data.get("items", [])
        if not items:
            return {"message": "No signals yet. Pay anyway."}
        top = items[0]
        return {
            "found": len(items),
            "top_score": top.get("score"),
            "region_hint": (top.get("why") or ["unknown"])[0],
            "message": f"Found {len(items)} talents. Top prospect: {top.get('score')}% breakout probability",
            "unlock_price": self.tiers["instant"]["price"],
            "unlock_url": "/api/pay/instant",
        }

    def tier_payload(self, tier: str) -> Dict[str, object]:
        if tier not in self.tiers:
            raise ValueError("unknown tier")
        tier_info = self.tiers[tier]
        data = self._load_latest()

        generated = data.get("generated_at_utc") or datetime.utcnow().isoformat() + "Z"
        generated_dt = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        now = datetime.utcnow().replace(tzinfo=generated_dt.tzinfo)
        hours_passed = (now - generated_dt).total_seconds() / 3600

        if tier == "free" and hours_passed < tier_info["delay_hours"]:
            return {
                "status": "delayed",
                "available_in": round(tier_info["delay_hours"] - hours_passed, 2),
                "unlock_now": self.tiers["instant"]["price"],
            }

        return {
            "status": "available",
            "data": data.get("items", [])[: tier_info["players"]],
        }

    # ---------------------- internals ----------------------
    def _load_latest(self) -> Dict[str, object]:
        if not self.data_path.exists():
            return {"items": []}
        try:
            return json.loads(self.data_path.read_text(encoding="utf-8"))
        except Exception:
            return {"items": []}


__all__ = ["OB1Paywall"]
