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
    # expressions de plusieurs mots (cherchées en premier)
    "coupe vent": "coupe-vent", "sac a dos": "sac à dos", "sac a main": "sac à main", "col roule": "pull col roulé",
    "veste de costume": "blazer", "maillot de bain": "maillot de bain", "tee shirt": "t-shirt",
    "sweat shirt": "sweat", "pull over": "pull", "bob": "bob",
    # autres types
    "windbreaker": "coupe-vent", "anorak": "anorak", "kway": "coupe-vent", "softshell": "veste softshell",
    "polaire": "polaire", "fleece": "polaire", "teddy": "veste teddy", "bomber": "bomber", "perfecto": "perfecto",
    "caban": "caban", "duffle": "duffle-coat", "imperméable": "imperméable", "impermeable": "imperméable",
    "sweatshirt": "sweat", "pullover": "pull", "salopette": "salopette", "kimono": "kimono", "poncho": "poncho",
    "cape": "cape", "body": "body", "brassiere": "brassière", "maillot": "maillot", "bikini": "bikini",
    "pyjama": "pyjama", "chaussettes": "chaussettes", "mules": "mules", "derbies": "derbies", "tongs": "tongs",
    "espadrilles": "espadrilles", "ballerines": "ballerines", "sneaker": "baskets", "runners": "baskets",
    "chaussures": "chaussures", "gants": "gants", "lunettes": "lunettes", "montre": "montre",
    "portefeuille": "portefeuille", "cabas": "cabas", "tote": "tote bag", "banane": "sac banane",
    "chino": "chino", "cargo": "pantalon cargo", "jogger": "jogging", "survetement": "survêtement",
    "tracksuit": "survêtement", "overshirt": "surchemise", "hoody": "sweat à capuche", "capuche": "sweat à capuche",
    "crop": "crop top", "corset": "corset", "jumpsuit": "combinaison", "overall": "salopette",
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


def _close(a: str, b: str) -> bool:
    """Vrai si a et b ne diffèrent que d'une lettre (changée, en trop ou en moins)."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    if len(a) > len(b):
        a, b = b, a
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


_VOCAB: Optional[set[str]] = None


def _vocab() -> set[str]:
    global _VOCAB
    if _VOCAB is None:
        words = set(TYPES) | set(COLORS) | {k for k, v in MATERIALS.items() if v}
        for b in known_brands():
            words |= {w for w in re.findall(r"[a-z&'.-]+", _plain(b)) if len(w) >= 4}
        _VOCAB = words
    return _VOCAB


def fix_word(w: str) -> str:
    """Corrige une faute d'une lettre sur un mot connu (type, couleur, matière, marque).
    Les mots courts (moins de 5 lettres) ne sont pas touchés pour éviter les fausses corrections."""
    vocab = _vocab()
    if len(w) < 5 or w in vocab or w.rstrip("s") in vocab:
        return w
    matches = sorted(v for v in vocab if len(v) >= 4 and _close(w, v))
    return matches[0] if len(matches) == 1 else w


def describe(item: Item) -> dict:
    """Type, couleur et matière repérés dans le titre et les champs connus."""
    text = " ".join(x for x in (item.category, item.model, item.color) if x)
    words = [fix_word(w) for w in re.findall(r"[a-z&']+", _plain(text).replace("-", " "))]
    joined = f" {' '.join(words)} "
    kind = next((TYPES[k] for k in TYPES if " " in k and f" {k} " in joined), None) or _find(words, TYPES)
    color = _find(words, COLORS)
    material = _find([w for w in words if w != kind], MATERIALS)
    return {"type": kind, "color": color, "material": material}


BRANDS = _build_brands()


STOP = {"a", "de", "du", "des", "la", "le", "les", "en", "et", "pour", "avec", "the", "and", "with", "homme",
        "femme", "unisexe", "men", "women", "kids", "enfant", "taille", "size", "new", "neuf", "collection"}


def core_words(item: Item, brand: str = "") -> list[str]:
    """Mots utiles du titre, sans la marque, les petits mots ni les références."""
    words = [fix_word(w) for w in re.findall(r"[a-z&']+", _plain(item.model or "").replace("-", " "))]
    brand_words = set(brand.split()) | set(_key(item.brand or "").split())
    return list(dict.fromkeys(w for w in words if w not in STOP and w not in brand_words and len(w) > 1))


def broaden(item: Item) -> None:
    """Ajoute une recherche plus large (marque + type + couleur) s'il n'y en a qu'une."""
    if len(item.queries) >= 2:
        return
    d = describe(item)
    brand = _plain(item.brand or "")
    core = [x for x in (d["type"], d["color"]) if x] or core_words(item, brand)[:2]
    broad = " ".join([brand] + core if brand else core).strip()
    if broad and broad not in item.queries:
        item.queries.append(broad)


def similar(item: Item) -> Optional[dict]:
    """Recherche « toutes marques » et marques proches, ou None si rien d'utile dans le titre."""
    d = describe(item)
    brand = _key(item.brand or "")
    brand = _key(ALIASES.get(brand, brand))
    if brand not in BRANDS:  # marque absente de la fiche : on la cherche dans le titre
        title = f" {_plain(item.model or '')} "
        brand = next((_key(b) for b in known_brands() if f" {_key(b)} " in title), brand)
    brands = [b for b in BRANDS.get(brand, []) if _key(b) != brand][:MAX_BRANDS]
    if d["type"]:
        query = " ".join(x for x in (d["type"], d["color"], d["material"]) if x)
        short = " ".join(x for x in (d["type"], d["color"]) if x)
    else:  # type inconnu : on garde les mots du titre sans la marque (ex. « capuche noir »)
        core = core_words(item, brand)
        if not core:
            return None
        query = " ".join(core[:4])
        short = " ".join(core[:3])
    return {
        "query": query,
        "brands": [{"brand": b, "query": f"{b} {short}".lower()} for b in brands],
    }
