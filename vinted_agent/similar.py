"""Articles qui ressemblent, dans d'autres marques (sans IA, à partir des mots du titre).

On repère le type de vêtement, la couleur et la matière dans le titre de la page produit,
puis on propose une recherche « toutes marques » et quelques marques du même style.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from .models import Item

# mot trouvé dans le titre -> mot utilisé pour la recherche
TYPES = {
    "veste": "veste", "blouson": "blouson", "manteau": "manteau", "doudoune": "doudoune", "parka": "parka",
    "trench": "trench", "blazer": "blazer", "gilet": "gilet", "cardigan": "cardigan", "pull": "pull",
    "sweat": "sweat", "tee": "t-shirt", "hoodie": "sweat à capuche", "t-shirt": "t-shirt", "tee-shirt": "t-shirt", "tshirt": "t-shirt",
    "debardeur": "débardeur", "top": "top", "chemise": "chemise", "surchemise": "surchemise", "blouse": "blouse",
    "polo": "polo", "robe": "robe", "jupe": "jupe", "jean": "jean", "pantalon": "pantalon", "short": "short",
    "legging": "legging", "jogging": "jogging", "combinaison": "combinaison", "costume": "costume",
    "baskets": "baskets", "basket": "baskets", "sneakers": "baskets", "bottes": "bottes", "bottines": "bottines",
    "boots": "boots", "mocassins": "mocassins", "sandales": "sandales", "escarpins": "escarpins",
    "sac": "sac", "pochette": "pochette", "ceinture": "ceinture", "echarpe": "écharpe", "bonnet": "bonnet",
    "casquette": "casquette", "jacket": "veste", "coat": "manteau", "dress": "robe", "skirt": "jupe",
    "jeans": "jean", "trousers": "pantalon", "shirt": "chemise", "jumper": "pull", "sweater": "pull",
    "trainers": "baskets", "bag": "sac",
}
COLORS = {
    "noir": "noir", "noire": "noir", "blanc": "blanc", "blanche": "blanc", "ecru": "écru", "beige": "beige",
    "camel": "camel", "marron": "marron", "chocolat": "marron", "brun": "marron", "taupe": "taupe",
    "gris": "gris", "grise": "gris", "anthracite": "gris", "bleu": "bleu", "bleue": "bleu", "marine": "bleu marine",
    "vert": "vert", "verte": "vert", "kaki": "kaki", "rouge": "rouge", "bordeaux": "bordeaux", "rose": "rose",
    "violet": "violet", "violette": "violet", "jaune": "jaune", "orange": "orange", "dore": "doré", "argent": "argenté",
    "black": "noir", "white": "blanc", "brown": "marron", "grey": "gris", "gray": "gris", "blue": "bleu",
    "navy": "bleu marine", "green": "vert", "red": "rouge", "pink": "rose",
}
MATERIALS = {
    "cuir": "cuir", "daim": "daim", "suede": "daim", "suedine": "suédine", "laine": "laine", "cachemire": "cachemire",
    "lin": "lin", "velours": "velours", "denim": "denim", "jean": None, "satin": "satin", "satine": "satin", "satinee": "satin", "soie": "soie",
    "maille": "maille", "polaire": "polaire", "moumoute": "moumoute", "sherpa": "sherpa", "leather": "cuir",
    "wool": "laine", "linen": "lin", "corduroy": "velours côtelé",
}
# Familles de marques du même style et d'une gamme de prix proche.
# Les « marques proches » d'une marque sont les autres marques de sa (ou ses) famille(s).
GROUPS = {
    "fast fashion": ["Zara", "Mango", "H&M", "Pull&Bear", "Bershka", "Stradivarius", "Primark", "Kiabi",
                     "Jennyfer", "Pimkie", "Promod", "Camaïeu", "Shein", "Asos", "New Look", "Monki", "Weekday",
                     "Only", "Vero Moda", "Jack & Jones", "Celio", "Bonobo", "Jules", "Brice"],
    "basiques qualité": ["Uniqlo", "Arket", "COS", "Massimo Dutti", "& Other Stories", "Muji", "Gap",
                         "Benetton", "Esprit", "Marks & Spencer"],
    "parisien chic": ["Sézane", "Rouje", "Ba&sh", "Maje", "Sandro", "Claudie Pierlot", "The Kooples",
                      "Zadig & Voltaire", "IRO", "Sessùn", "Soeur", "Vanessa Bruno", "Isabel Marant Étoile",
                      "A.P.C.", "American Vintage", "Des Petits Hauts", "Comptoir des Cotonniers",
                      "Gérard Darel", "Ekyog", "Musier"],
    "français casual": ["Le Slip Français", "Armor-Lux", "Saint James", "Faguo", "Jules", "Celio", "Bonobo",
                        "Cyrillus", "Petit Bateau", "Okaïdi", "Tape à l'œil", "Aigle", "Façonnable"],
    "preppy": ["Ralph Lauren", "Lacoste", "Tommy Hilfiger", "Gant", "Fred Perry", "Hackett", "Brooks Brothers",
               "Polo Ralph Lauren", "Façonnable", "Serge Blanco", "Eden Park", "La Martina", "Calvin Klein"],
    "sport": ["Nike", "Adidas", "Puma", "Reebok", "New Balance", "Asics", "Under Armour", "Fila", "Kappa",
              "Champion", "Le Coq Sportif", "Umbro", "Jordan", "Decathlon", "Kalenji"],
    "running": ["Asics", "Saucony", "Mizuno", "Hoka", "Brooks", "On", "New Balance", "Salomon"],
    "sneakers": ["Nike", "Adidas", "New Balance", "Vans", "Converse", "Veja", "Puma", "Reebok", "Asics",
                 "Autry", "Golden Goose", "Common Projects", "Axel Arigato", "Saucony"],
    "streetwear": ["Carhartt", "Stüssy", "Supreme", "Palace", "The North Face", "Obey", "Huf", "Element",
                   "Dickies", "Champion", "Kith", "Off-White", "Corteiz", "Trapstar", "Sixth June",
                   "Wasted Paris", "Ellesse", "Sergio Tacchini"],
    "skate & surf": ["Vans", "DC Shoes", "Element", "Volcom", "Quiksilver", "Billabong", "Rip Curl",
                     "Roxy", "Oxbow", "Santa Cruz", "Thrasher", "Globe"],
    "outdoor": ["The North Face", "Patagonia", "Columbia", "Arc'teryx", "Salomon", "Quechua", "Helly Hansen",
                "Fjällräven", "Jack Wolfskin", "Millet", "Mammut", "Aigle", "Rab", "Napapijri", "Timberland"],
    "doudounes premium": ["Moncler", "Canada Goose", "Pyrenex", "Woolrich", "Save The Duck", "Napapijri",
                          "Parajumpers", "K-Way", "Herno"],
    "denim": ["Levi's", "Lee", "Wrangler", "Diesel", "G-Star", "Pepe Jeans", "Tommy Jeans", "Calvin Klein Jeans",
              "Kaporal", "Le Temps des Cerises", "Salsa", "Mustang", "Acne Studios", "Nudie Jeans", "Edwin"],
    "chaussures": ["Dr. Martens", "Timberland", "Clarks", "Birkenstock", "UGG", "Minelli", "San Marina",
                   "Bocage", "Mephisto", "Geox", "Paraboot", "Kickers", "Palladium", "Bensimon", "Sorel"],
    "premium": ["Acne Studios", "AMI Paris", "Maison Kitsuné", "Jacquemus", "A.P.C.", "Sandro", "The Kooples",
                "Zadig & Voltaire", "Isabel Marant", "Ganni", "Marine Serre", "Axel Arigato", "Stone Island",
                "CP Company", "Hugo Boss", "Tommy Hilfiger", "Michael Kors", "Coach"],
    "luxe": ["Gucci", "Prada", "Louis Vuitton", "Chanel", "Dior", "Saint Laurent", "Balenciaga", "Celine",
             "Hermès", "Fendi", "Givenchy", "Valentino", "Burberry", "Bottega Veneta", "Loewe", "Miu Miu",
             "Versace", "Moncler", "Alexander McQueen", "Off-White"],
    "sacs": ["Longchamp", "Lancel", "Le Tanneur", "Michael Kors", "Coach", "Kate Spade", "Polène", "Sézane",
             "Jérôme Dreyfuss", "Vanessa Bruno", "Furla", "Guess", "Fossil"],
    "lingerie & bain": ["Etam", "Undiz", "Princesse tam.tam", "Darjeeling", "Calvin Klein", "Intimissimi",
                        "Victoria's Secret", "Aubade", "Simone Pérèle", "Banana Moon", "Seafolly"],
    "enfant": ["Petit Bateau", "Jacadi", "Cyrillus", "Okaïdi", "Tape à l'œil", "Du Pareil au Même", "Vertbaudet",
               "Catimini", "Zara Kids", "H&M Kids", "Bonpoint", "Kiabi"],
}
ALIASES = {"levis": "levi's", "hm": "h&m", "h et m": "h&m", "zv": "zadig & voltaire", "tnf": "the north face", "north face": "the north face",
           "dr martens": "dr. martens", "docs": "dr. martens", "ralph": "ralph lauren", "ysl": "saint laurent",
           "lv": "louis vuitton", "stussy": "stüssy", "arcteryx": "arc'teryx", "other stories": "& other stories",
           "sezane": "sézane", "apc": "a.p.c.", "cp": "cp company", "tommy": "tommy hilfiger"}


MAX_BRANDS = 6


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _find(words: list[str], table: dict) -> Optional[str]:
    for w in words:
        for form in (w, w[:-1] if w.endswith("s") else None, w[:-2] if w.endswith("es") else None):
            if form and table.get(form):
                return table[form]
    return None


def _key(name: str) -> str:
    return _plain(name).strip()


def _build_brands() -> dict[str, list[str]]:
    # Pour chaque marque, on parcourt d'abord la famille où elle apparaît le plus tôt (sa famille
    # « principale »), et dans chaque famille les voisins les plus proches dans la liste d'abord.
    homes: dict[str, list[tuple[int, list[str]]]] = {}
    for members in GROUPS.values():
        for i, b in enumerate(members):
            homes.setdefault(b, []).append((i, members))
    out: dict[str, list[str]] = {}
    for b, places in homes.items():
        lst: list[str] = []
        for i, members in sorted(places, key=lambda p: p[0]):
            others = sorted((m for m in members if m != b), key=lambda m: abs(members.index(m) - i))
            lst += [m for m in others if m not in lst]
        out[_key(b)] = lst
    return out


def known_brands() -> list[str]:
    """Toutes les marques connues (pour les repérer dans un titre ou une adresse)."""
    return sorted({b for members in GROUPS.values() for b in members}, key=len, reverse=True)


def describe(item: Item) -> dict:
    """Type, couleur et matière repérés dans le titre et les champs connus."""
    text = " ".join(x for x in (item.category, item.model, item.color) if x)
    words = re.findall(r"[a-z&'-]+", _plain(text))
    kind = _find(words, TYPES)
    color = _find(words, COLORS)
    material = _find([w for w in words if w != kind], MATERIALS)
    return {"type": kind, "color": color, "material": material}


BRANDS = _build_brands()


def similar(item: Item) -> Optional[dict]:
    """Recherche « toutes marques » et marques proches, ou None si le type n'est pas reconnu."""
    d = describe(item)
    if not d["type"]:
        return None
    query = " ".join(x for x in (d["type"], d["color"], d["material"]) if x)
    brand = _key(item.brand or "")
    brand = ALIASES.get(brand, brand)
    if brand not in BRANDS:  # marque absente de la fiche : on la cherche dans le titre
        title = f" {_plain(item.model or '')} "
        brand = next((_key(b) for b in known_brands() if f" {_key(b)} " in title), brand)
    brands = [b for b in BRANDS.get(brand, []) if _key(b) != brand][:MAX_BRANDS]
    short = " ".join(x for x in (d["type"], d["color"]) if x)
    return {
        "query": query,
        "brands": [{"brand": b, "query": f"{b} {short}".lower()} for b in brands],
    }
