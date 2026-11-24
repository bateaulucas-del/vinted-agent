"""Recherche sur Vinted via l'API interne du site web.

Vinted n'a pas d'API publique : on reproduit ce que fait le navigateur.
Ses conditions d'utilisation interdisent la collecte automatisée, donc à
réserver à un usage personnel, à faible volume, avec des pauses.
"""
from __future__ import annotations

import time
from typing import Optional

import requests

from .identify import HEADERS
from .models import Listing

DOMAIN = "https://www.vinted.fr"
MIN_DELAY = 2.0  # secondes entre deux appels, pour rester raisonnable


class VintedClient:
    def __init__(self, domain: str = DOMAIN):
        self.domain = domain.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.headers["Accept"] = "application/json, text/plain, */*"
        self._last_call = 0.0
        self._ready = False

    def _wait(self):
        delta = time.time() - self._last_call
        if delta < MIN_DELAY:
            time.sleep(MIN_DELAY - delta)
        self._last_call = time.time()

    def _init_cookies(self):
        # La page d'accueil pose le cookie de session anonyme exigé par l'API.
        self._wait()
        self.session.get(self.domain + "/", timeout=20)
        self._ready = True

    def search(self, query: str, per_page: int = 30, price_to: Optional[float] = None,
               order: str = "relevance") -> list[Listing]:
        if not self._ready:
            self._init_cookies()
        params = {"search_text": query, "per_page": per_page, "page": 1, "order": order}
        if price_to:
            params["price_to"] = price_to
        for attempt in range(2):
            self._wait()
            r = self.session.get(self.domain + "/api/v2/catalog/items", params=params, timeout=20)
            if r.status_code == 401 and attempt == 0:
                self._init_cookies()  # cookie expiré : on le renouvelle une fois
                continue
            if r.status_code == 429:
                raise RuntimeError("Vinted limite les requêtes (429). Réessaie dans quelques minutes.")
            if r.status_code == 403:
                raise RuntimeError(
                    "Vinted a bloqué la requête (403, protection anti-robot). "
                    "Réessaie plus tard ou depuis un autre réseau."
                )
            r.raise_for_status()
            return [self._to_listing(x) for x in r.json().get("items", [])]
        return []

    def _to_listing(self, x: dict) -> Listing:
        price = x.get("price")
        if isinstance(price, dict):
            amount, currency = price.get("amount"), price.get("currency_code", "EUR")
        else:
            amount, currency = price, x.get("currency", "EUR")
        photo = x.get("photo") or {}
        user = x.get("user") or {}
        url = x.get("url") or f"{self.domain}/items/{x.get('id')}"
        if url.startswith("/"):
            url = self.domain + url
        return Listing(
            id=x["id"],
            title=x.get("title", ""),
            price=float(amount or 0),
            currency=currency or "EUR",
            brand=x.get("brand_title"),
            size=x.get("size_title"),
            condition=x.get("status"),
            url=url,
            photo_url=photo.get("url"),
            seller=user.get("login"),
        )
