"""Conversion MAD sécurisée pour les revenus MRE, sans clé API."""

from __future__ import annotations

import json
from typing import TypedDict
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FALLBACK_RATES_TO_MAD = {"MAD": 1.0, "EUR": 10.80, "USD": 9.90}


class CurrencyConversion(TypedDict):
    currency: str
    rate: float
    source: str


def get_mad_rate(currency: str) -> CurrencyConversion:
    """Retourne le taux Frankfurter ou un taux de sécurité de continuité."""
    normalized_currency = currency.upper()
    if normalized_currency not in FALLBACK_RATES_TO_MAD:
        raise ValueError("La devise doit être MAD, EUR ou USD.")
    if normalized_currency == "MAD":
        return {"currency": "MAD", "rate": 1.0, "source": "identity"}
    query = urlencode({"from": normalized_currency, "to": "MAD"})
    try:
        request = Request(
            f"https://api.frankfurter.app/latest?{query}",
            headers={"User-Agent": "EQDOMFastTrack/1.0"},
        )
        with urlopen(request, timeout=2.5) as response:  # nosec B310 - URL contrôlée
            payload = json.loads(response.read().decode("utf-8"))
        rate = float(payload["rates"]["MAD"])
        if rate > 0:
            return {"currency": normalized_currency, "rate": rate, "source": "frankfurter"}
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        pass
    return {
        "currency": normalized_currency,
        "rate": FALLBACK_RATES_TO_MAD[normalized_currency],
        "source": "fallback",
    }
