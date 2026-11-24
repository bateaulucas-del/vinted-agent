"""Donner un score à chaque annonce selon sa ressemblance avec l'article recherché."""
from __future__ import annotations

import re
import unicodedata

from .models import Item, Listing

EXACT_THRESHOLD = 0.75


def _norm(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())


NOISE = {"homme", "femme", "unisexe", "enfant", "men", "women", "pour", "les", "des", "the", "and", "avec"}


def _tokens(s: str | None) -> set[str]:
    return {t for t in _norm(s).split() if len(t) > 1 and t not in NOISE}


def _close(a: str, b: str) -> bool:
    """Mots proches : identiques, ou même racine (blanc / blanche)."""
    return a == b or (len(a) >= 4 and len(b) >= 4 and a[:4] == b[:4])


def _matches(words: set[str], title: set[str]) -> int:
    return sum(1 for w in words if any(_close(w, t) for t in title))


def score(item: Item, listing: Listing) -> float:
    """Score entre 0 et 1. Marque 35 %, modèle 40 %, couleur 15 %, taille 10 %."""
    title = _tokens(listing.title) | _tokens(listing.brand)
    total = 0.0
    weight = 0.0

    if item.brand:
        weight += 0.35
        if _norm(item.brand).strip() and _norm(item.brand).strip() == _norm(listing.brand).strip():
            total += 0.35
        elif _tokens(item.brand) <= title:
            total += 0.30

    model_tokens = _tokens(item.model) - _tokens(item.brand)
    if model_tokens:
        weight += 0.40
        total += 0.40 * _matches(model_tokens, title) / len(model_tokens)

    if item.color:
        weight += 0.15
        if _matches(_tokens(item.color), title):
            total += 0.15

    if item.size and listing.size:
        weight += 0.10
        if _norm(item.size).strip() in _norm(listing.size).split():
            total += 0.10

    return round(total / weight, 3) if weight else 0.0


def rank(item: Item, listings: list[Listing]) -> list[Listing]:
    seen: dict[int, Listing] = {}
    for l in listings:
        if l.id not in seen:
            l.score = score(item, l)
            seen[l.id] = l
    return sorted(seen.values(), key=lambda l: (-l.score, l.price))
