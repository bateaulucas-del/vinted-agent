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
# marque -> marques du même style et de prix proche
BRANDS = {
    "zara": ["Mango", "Massimo Dutti", "H&M", "Pull&Bear"],
    "mango": ["Zara", "Massimo Dutti", "& Other Stories"],
    "h&m": ["Zara", "Mango", "Uniqlo", "Pull&Bear"],
    "pull&bear": ["Bershka", "Zara", "H&M"],
    "bershka": ["Pull&Bear", "Stradivarius", "Zara"],
    "stradivarius": ["Bershka", "Mango", "Zara"],
    "massimo dutti": ["Mango", "COS", "Zara", "Sézane"],
    "cos": ["Arket", "Massimo Dutti", "& Other Stories"],
    "arket": ["COS", "Uniqlo", "Massimo Dutti"],
    "uniqlo": ["Arket", "H&M", "Muji"],
    "sezane": ["Rouje", "Ba&sh", "& Other Stories"],
    "sandro": ["Maje", "The Kooples", "Claudie Pierlot"],
    "maje": ["Sandro", "Ba&sh", "Claudie Pierlot"],
    "ba&sh": ["Sézane", "Maje", "Sandro"],
    "the kooples": ["Sandro", "AllSaints", "Zadig & Voltaire"],
    "zadig & voltaire": ["The Kooples", "Sandro", "IRO"],
    "nike": ["Adidas", "New Balance", "Puma", "Asics"],
    "adidas": ["Nike", "Puma", "New Balance", "Reebok"],
    "new balance": ["Asics", "Nike", "Adidas", "Saucony"],
    "puma": ["Adidas", "Nike", "Reebok"],
    "asics": ["New Balance", "Saucony", "Mizuno"],
    "levi's": ["Lee", "Wrangler", "Carhartt"],
    "carhartt": ["Dickies", "Levi's", "Patagonia"],
    "the north face": ["Patagonia", "Columbia", "Arc'teryx"],
    "ralph lauren": ["Tommy Hilfiger", "Lacoste", "Gant"],
    "lacoste": ["Ralph Lauren", "Fred Perry", "Tommy Hilfiger"],
    "tommy hilfiger": ["Ralph Lauren", "Lacoste", "Calvin Klein"],
}
MAX_BRANDS = 4


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _find(words: list[str], table: dict) -> Optional[str]:
    for w in words:
        for form in (w, w[:-1] if w.endswith("s") else None, w[:-2] if w.endswith("es") else None):
            if form and table.get(form):
                return table[form]
    return None


def describe(item: Item) -> dict:
    """Type, couleur et matière repérés dans le titre et les champs connus."""
    text = " ".join(x for x in (item.category, item.model, item.color) if x)
    words = re.findall(r"[a-z&'-]+", _plain(text))
    kind = _find(words, TYPES)
    color = _find(words, COLORS)
    material = _find([w for w in words if w != kind], MATERIALS)
    return {"type": kind, "color": color, "material": material}


def similar(item: Item) -> Optional[dict]:
    """Recherche « toutes marques » et marques proches, ou None si le type n'est pas reconnu."""
    d = describe(item)
    if not d["type"]:
        return None
    query = " ".join(x for x in (d["type"], d["color"], d["material"]) if x)
    brand = _plain(item.brand or "").strip()
    brands = [b for b in BRANDS.get(brand, []) if _plain(b) != brand][:MAX_BRANDS]
    short = " ".join(x for x in (d["type"], d["color"]) if x)
    return {
        "query": query,
        "brands": [{"brand": b, "query": f"{b} {short}".lower()} for b in brands],
    }
