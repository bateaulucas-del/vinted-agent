"""Filtres de recherche choisis par le visiteur, appliqués aux liens de chaque site."""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# état -> identifiant Vinted (status_ids)
CONDITIONS = {"new_tags": "6", "new": "1", "very_good": "2", "good": "3", "ok": "4"}
GENDERS = {"women": "femme", "men": "homme", "kids": "enfant"}
SORTS = {"relevance", "price", "newest"}
SITES = {"Vinted", "eBay", "Leboncoin", "Vestiaire Collective"}


@dataclass
class Filters:
    conditions: list[str] = field(default_factory=list)
    sort: str = "relevance"
    gender: str = ""
    sites: set[str] = field(default_factory=lambda: set(SITES))

    @classmethod
    def parse(cls, conditions: list[str] | None, sort: str | None, gender: str | None,
              sites: list[str] | None) -> "Filters":
        return cls(
            conditions=[c for c in (conditions or []) if c in CONDITIONS],
            sort=sort if sort in SORTS else "relevance",
            gender=gender if gender in GENDERS else "",
            sites={s for s in (sites or []) if s in SITES} or set(SITES),
        )

    def query(self, q: str) -> str:
        """Ajoute « femme », « homme » ou « enfant » à la recherche si demandé."""
        word = GENDERS.get(self.gender)
        return f"{q} {word}" if word and word not in q.split() else q

    def url(self, url: str, newest: bool = False) -> str:
        """Ajoute l'état et le tri aux paramètres du lien, selon le site."""
        parts = urlsplit(url)
        params = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)]
        host = parts.netloc
        sort = "newest" if newest else self.sort
        if "vinted." in host:
            params = [(k, v) for k, v in params if k not in ("order", "status_ids[]")]
            params.append(("order", {"price": "price_low_to_high", "newest": "newest_first"}.get(sort, "relevance")))
            params += [("status_ids[]", CONDITIONS[c]) for c in self.conditions]
        elif "ebay." in host:
            params = [(k, v) for k, v in params if k not in ("_sop", "LH_ItemCondition")]
            new = any(c in ("new_tags", "new") for c in self.conditions)
            used = not self.conditions or any(c not in ("new_tags", "new") for c in self.conditions)
            params.append(("LH_ItemCondition", "|".join(x for x, ok in (("1000", new), ("3000", used)) if ok)))
            if sort in ("price", "newest"):
                params.append(("_sop", "15" if sort == "price" else "10"))
        elif "leboncoin." in host and sort in ("price", "newest"):
            params = [(k, v) for k, v in params if k not in ("sort", "order")]
            params += [("sort", "price"), ("order", "asc")] if sort == "price" else [("sort", "time"), ("order", "desc")]
        return urlunsplit(parts._replace(query=urlencode(params)))
