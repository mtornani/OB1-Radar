"""Flask API that guards the paywall."""
from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from flask import Flask, abort, jsonify, request
import stripe

from core import config
from monetize.paywall import OB1Paywall


app = Flask(__name__)
paywall = OB1Paywall()

if config.STRIPE_KEY:
    stripe.api_key = config.STRIPE_KEY


@app.get("/health")
def health() -> str:
    return "alive"


@app.get("/api/teaser")
def teaser() -> Any:
    return jsonify(paywall.generate_teaser())


@app.get("/api/data/<tier>")
def get_data(tier: str):
    try:
        payload = paywall.tier_payload(tier)
    except ValueError:
        abort(HTTPStatus.NOT_FOUND)
    return jsonify(payload)


@app.post("/api/pay")
def pay():
    if not config.STRIPE_KEY:
        abort(HTTPStatus.SERVICE_UNAVAILABLE)

    body = request.get_json(silent=True) or {}
    product = body.get("product", "instant")
    metadata = {"product": product}
    amount = _price_for_product(product)
    if amount <= 0:
        abort(HTTPStatus.BAD_REQUEST)

    player = body.get("player")
    if player:
        metadata["player"] = player

    intent = stripe.PaymentIntent.create(amount=amount, currency="eur", metadata=metadata)
    return jsonify({"client_secret": intent.client_secret})


def _price_for_product(product: str) -> int:
    if product == "instant":
        return int(config.PRICING["instant"] * 100)
    if product == "certificate":
        return int(config.PRICING["certificate"] * 100)
    if product == "pro":
        return int(config.PRICING["monthly"] * 100)
    if product == "insider":
        return int(config.PRICING["insider"] * 100)
    return 0


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
