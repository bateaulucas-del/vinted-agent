"""Où trouver l'article d'occasion : un lien par site, et le nombre d'annonces quand c'est possible.

Seul eBay a une API officielle et gratuite qui donne un nombre d'annonces (Browse API).
Vinted, Leboncoin et Vestiaire Collective n'en ont pas et interdisent la collecte
automatisée : pour eux on ne donne qu'un lien, ouvert par le visiteur lui-même.

Pour activer le compteur eBay, définir EBAY_CLIENT_ID et EBAY_CLIENT_SECRET
(clés « Production » d'un compte développeur eBay gratuit).
"""
from __future__ import annotations

import base64
import os
import time
from typing import Optional
from urllib.parse import quote_plus, urlencode

import requests

from .links import search_url as vinted_url

EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
EBAY = {  # pays du site -> (place de marché, domaine, devise)
    "fr": ("EBAY_FR", "www.ebay.fr", "EUR"),
    "be": ("EBAY_BE", "www.befr.ebay.be", "EUR"),
    "es": ("EBAY_ES", "www.ebay.es", "EUR"),
    "it": ("EBAY_IT", "www.ebay.it", "EUR"),
    "de": ("EBAY_DE", "www.ebay.de", "EUR"),
    "uk": ("EBAY_GB", "www.ebay.co.uk", "GBP"),
}
VESTIAIRE = {"fr": "fr", "be": "fr", "es": "es", "it": "it", "de": "de", "uk": "uk"}
CACHE_SECONDS = 3600

_token: dict = {"value": None, "expires": 0.0}
_cache: dict[tuple, tuple[float, Optional[int]]] = {}


def ebay_enabled() -> bool:
    return bool(os.environ.get("EBAY_CLIENT_ID") and os.environ.get("EBAY_CLIENT_SECRET"))


def _ebay_token() -> str:
    if _token["value"] and _token["expires"] > time.time() + 60:
        return _token["value"]
    creds = f"{os.environ['EBAY_CLIENT_ID']}:{os.environ['EBAY_CLIENT_SECRET']}".encode()
    r = requests.post(
        EBAY_TOKEN_URL,
        headers={"Authorization": "Basic " + base64.b64encode(creds).decode(),
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    _token["value"] = data["access_token"]
    _token["expires"] = time.time() + int(data.get("expires_in", 7200))
    return _token["value"]


def ebay_count(query: str, max_price: Optional[float], country: str) -> Optional[int]:
    """Nombre d'annonces d'occasion eBay pour cette recherche, ou None si indisponible."""
    if not ebay_enabled():
        return None
    marketplace, _, currency = EBAY.get(country, EBAY["fr"])
    key = (query.lower(), max_price, marketplace)
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    filters = ["conditions:{USED}"]
    if max_price:
        filters += [f"price:[..{max_price:g}]", f"priceCurrency:{currency}"]
    try:
        r = requests.get(
            EBAY_SEARCH_URL,
            headers={"Authorization": "Bearer " + _ebay_token(), "X-EBAY-C-MARKETPLACE-ID": marketplace},
            params={"q": query, "limit": 1, "filter": ",".join(filters)},
            timeout=10,
        )
        r.raise_for_status()
        total: Optional[int] = int(r.json().get("total", 0))
    except Exception:
        total = None
    _cache[key] = (time.time() + (CACHE_SECONDS if total is not None else 120), total)
    return total


def ebay_url(query: str, max_price: Optional[float], country: str) -> str:
    _, domain, _ = EBAY.get(country, EBAY["fr"])
    params = {"_nkw": query, "LH_ItemCondition": "3000"}  # 3000 = occasion
    if max_price:
        params["_udhi"] = f"{max_price:g}"
    return f"https://{domain}/sch/i.html?{urlencode(params)}"


def site_results(query: str, max_price: Optional[float] = None, country: str = "fr") -> list[dict]:
    """Une ligne par site : nom, lien de recherche, nombre d'annonces (None = non disponible)."""
    rows = [
        {"site": "Vinted", "url": vinted_url(query, max_price, country=country), "count": None},
        {"site": "eBay", "url": ebay_url(query, max_price, country), "count": ebay_count(query, max_price, country)},
    ]
    if country == "fr":
        price = f"&price=min-{max_price:g}" if max_price else ""
        rows.append({"site": "Leboncoin", "count": None,
                     "url": f"https://www.leboncoin.fr/recherche?text={quote_plus(query)}{price}"})
    rows.append({"site": "Vestiaire Collective", "count": None,
                 "url": f"https://{VESTIAIRE.get(country, 'fr')}.vestiairecollective.com/search/?q={quote_plus(query)}"})
    return rows
