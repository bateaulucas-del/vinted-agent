"""Le cœur de l'agent : identifier, chercher, classer. Réutilisable par l'appli web."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .identify import item_from_photo, item_from_url
from .models import Item, Listing
from .ranking import EXACT_THRESHOLD, rank
from .vinted import VintedClient


@dataclass
class Result:
    item: Item
    exact: list[Listing]
    similar: list[Listing]


def find(source: str, size: Optional[str] = None, max_price: Optional[float] = None,
         limit: int = 10, client: Optional[VintedClient] = None) -> Result:
    if source.startswith(("http://", "https://")):
        item = item_from_url(source)
    else:
        item = item_from_photo(source)
    if size:
        item.size = size

    client = client or VintedClient()
    listings: list[Listing] = []
    for q in item.queries[:3]:
        listings += client.search(q, price_to=max_price)
        # Si la requête précise donne déjà de bons résultats, inutile d'élargir
        if sum(1 for l in rank(item, listings) if l.score >= EXACT_THRESHOLD) >= limit:
            break

    ranked = rank(item, listings)
    if size:
        ranked = [l for l in ranked if not l.size or size.lower() in l.size.lower().split()] or ranked
    exact = [l for l in ranked if l.score >= EXACT_THRESHOLD][:limit]
    similar = [l for l in ranked if l.score < EXACT_THRESHOLD][: max(0, limit - len(exact))]
    return Result(item=item, exact=exact, similar=similar)
