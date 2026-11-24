"""Utilisation : python -m vinted_agent <lien ou photo> [--taille M] [--prix-max 40]"""
from __future__ import annotations

import argparse
import sys

from .agent import find
from .models import Listing


def _line(l: Listing, retail: float | None) -> str:
    deal = ""
    if retail and l.price:
        deal = f"  ({round(100 * (1 - l.price / retail))} % sous le neuf)"
    bits = [f"{l.price:.2f} {l.currency}{deal}", l.size or "", l.condition or ""]
    return (f"  • {l.title}\n    {' · '.join(b for b in bits if b)}  [score {l.score:.2f}]\n"
            f"    {l.url}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="vinted_agent",
                                description="Retrouve sur Vinted un vêtement vu sur un site ou en photo.")
    p.add_argument("source", help="Lien d'une page produit, ou chemin d'une photo")
    p.add_argument("--taille", help="Ta taille, ex. M ou 42")
    p.add_argument("--prix-max", type=float, help="Prix maximum en euros")
    p.add_argument("--nombre", type=int, default=10, help="Nombre d'annonces à afficher")
    a = p.parse_args(argv)

    try:
        r = find(a.source, size=a.taille, max_price=a.prix_max, limit=a.nombre)
    except Exception as e:
        print(f"Erreur : {e}", file=sys.stderr)
        return 1

    it = r.item
    print("Article identifié :")
    for label, v in [("Marque", it.brand), ("Modèle", it.model), ("Type", it.category),
                     ("Couleur", it.color), ("Taille", it.size),
                     ("Prix neuf", f"{it.retail_price:.2f} €" if it.retail_price else None)]:
        if v:
            print(f"  {label} : {v}")
    print(f"  Recherches : {', '.join(it.queries)}\n")

    if r.exact:
        print(f"✅ Même article trouvé ({len(r.exact)}) :")
        for l in r.exact:
            print(_line(l, it.retail_price))
    else:
        print("❌ Pas d'annonce pour cet article exact.")
    if r.similar:
        print(f"\nArticles proches ({len(r.similar)}) :")
        for l in r.similar:
            print(_line(l, it.retail_price))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
