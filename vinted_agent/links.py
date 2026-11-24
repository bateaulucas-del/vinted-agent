"""Fabrique des liens de recherche vinted.fr (aucune collecte : c'est le visiteur qui ouvre Vinted)."""
from __future__ import annotations

from typing import Optional
from urllib.parse import urlencode

from .models import Item

DOMAINS = {"fr": "https://www.vinted.fr", "be": "https://www.vinted.be", "es": "https://www.vinted.es",
           "it": "https://www.vinted.it", "de": "https://www.vinted.de", "uk": "https://www.vinted.co.uk"}


def search_url(query: str, max_price: Optional[float] = None, order: str = "relevance",
               country: str = "fr") -> str:
    params = {"search_text": query, "order": order}
    if max_price:
        params["price_to"] = f"{max_price:g}"
        params["currency"] = "GBP" if country == "uk" else "EUR"
    return f"{DOMAINS.get(country, DOMAINS['fr'])}/catalog?{urlencode(params)}"


def search_links(item: Item, size: Optional[str] = None, max_price: Optional[float] = None,
                 country: str = "fr") -> list[dict]:
    links = []
    for i, q in enumerate(item.queries[:3]):
        text = q  # la taille se règle dans les filtres Vinted (ses identifiants internes ne sont pas publics)
        label = "Article exact" if i == 0 else ("Plus large" if i == 1 else "Articles similaires")
        links.append({"label": label, "query": text,
                      "url": search_url(text, max_price, country=country),
                      "newest_url": search_url(text, max_price, order="newest_first", country=country)})
    return links
