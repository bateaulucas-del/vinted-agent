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
# Liste élargie : vêtements, chaussures, accessoires, en français et en anglais, avec les orthographes
# courantes. Les clés sont sans accents ni tirets (le titre est mis sous cette forme avant la recherche).
TYPES.update({
    # expressions de plusieurs mots (cherchées avant les mots seuls)
    "t shirt": "t-shirt", "tee shirts": "t-shirt", "t shirts": "t-shirt", "coupes vent": "coupe-vent",
    "k way": "coupe-vent", "rain jacket": "imperméable", "veste de pluie": "imperméable",
    "sweat a capuche": "sweat à capuche", "sweat capuche": "sweat à capuche", "half zip": "pull demi-zip",
    "quarter zip": "pull demi-zip", "demi zip": "pull demi-zip", "sous pull": "sous-pull",
    "tank top": "débardeur", "crop top": "crop top", "over shirt": "surchemise", "sur chemise": "surchemise",
    "chemise de nuit": "chemise de nuit", "robe de chambre": "robe de chambre", "robe de soiree": "robe de soirée",
    "doudoune sans manches": "doudoune sans manches", "gilet sans manches": "gilet sans manches",
    "veste sans manches": "gilet sans manches", "veste en jean": "veste en jean", "denim jacket": "veste en jean",
    "veste de travail": "veste de travail", "chore jacket": "veste de travail", "down jacket": "doudoune",
    "puffer jacket": "doudoune", "trench coat": "trench", "duffle coat": "duffle-coat", "pea coat": "caban",
    "veste matelassee": "veste matelassée", "gilet de costume": "gilet de costume",
    "jupe culotte": "jupe-culotte", "mini jupe": "mini-jupe", "pantalon de survetement": "pantalon de survêtement",
    "track pants": "pantalon de survêtement", "short de bain": "short de bain", "swim shorts": "short de bain",
    "maillot de foot": "maillot de foot", "maillot de football": "maillot de foot", "football shirt": "maillot de foot",
    "soutien gorge": "soutien-gorge", "nu pieds": "sandales", "flip flops": "tongs", "chelsea boots": "chelsea boots",
    "ankle boots": "bottines", "mary janes": "babies", "slip on": "baskets slip-on", "running shoes": "chaussures de running",
    "chaussures de running": "chaussures de running", "chaussures de sport": "baskets", "bottes de pluie": "bottes de pluie",
    "sac bandouliere": "sac bandoulière", "sac de sport": "sac de sport", "sac de voyage": "sac de voyage",
    "tote bag": "tote bag", "porte monnaie": "porte-monnaie", "porte cartes": "porte-cartes", "porte carte": "porte-cartes",
    "porte cles": "porte-clés", "tour de cou": "snood", "bucket hat": "bob", "noeud papillon": "nœud papillon",
    "lunettes de soleil": "lunettes de soleil", "boucles d'oreilles": "boucles d'oreilles",
    "boucles d oreilles": "boucles d'oreilles", "boucle d'oreille": "boucles d'oreilles",
    "combinaison de ski": "combinaison de ski", "pantalon de ski": "pantalon de ski", "veste de ski": "veste de ski",
    # hauts
    "chemisier": "chemisier", "tunique": "tunique", "tunic": "tunique", "bustier": "bustier", "caraco": "caraco",
    "camisole": "caraco", "marcel": "débardeur", "tank": "débardeur", "henley": "t-shirt henley",
    "longsleeve": "t-shirt manches longues", "tricot": "pull", "knit": "pull", "knitwear": "pull",
    "crewneck": "sweat", "sweatshirts": "sweat", "hoodies": "sweat à capuche", "bolero": "boléro",
    "shacket": "surchemise", "bodysuit": "body", "blouses": "blouse", "tshirts": "t-shirt", "tees": "t-shirt",
    "cardi": "cardigan", "gilets": "gilet", "jersey": "maillot", "maillots": "maillot",
    # vestes et manteaux
    "puffer": "doudoune", "pardessus": "manteau", "overcoat": "manteau", "peacoat": "caban", "trenchcoat": "trench",
    "vareuse": "vareuse", "saharienne": "saharienne", "harrington": "veste harrington", "varsity": "veste teddy",
    "letterman": "veste teddy", "biker": "perfecto", "aviateur": "blouson aviateur", "shearling": "veste en peau lainée",
    "vest": "gilet", "waistcoat": "gilet de costume", "raincoat": "imperméable", "cire": "ciré",
    "hardshell": "veste imperméable", "loden": "manteau loden", "doudounes": "doudoune", "blazers": "blazer",
    "jackets": "veste", "coats": "manteau", "matelassee": "veste matelassée", "quilted": "veste matelassée",
    "gabardine": "trench", "smoking": "costume", "tailleur": "tailleur", "suit": "costume",
    # bas
    "bermuda": "bermuda", "pantacourt": "pantacourt", "corsaire": "pantacourt", "jegging": "jegging",
    "flare": "pantalon évasé", "palazzo": "pantalon palazzo", "chinos": "chino", "joggers": "jogging",
    "sweatpants": "jogging", "joggings": "jogging", "trackpants": "pantalon de survêtement", "shorts": "short",
    "minijupe": "mini-jupe", "jupon": "jupon", "pants": "pantalon", "slacks": "pantalon", "skort": "jupe-short",
    "culotte": "culotte", "collant": "collants", "tights": "collants", "leggings": "legging", "pantalons": "pantalon",
    "combishort": "combishort", "playsuit": "combishort", "romper": "combishort", "barboteuse": "barboteuse",
    "salopettes": "salopette", "dungarees": "salopette", "baggy": "jean baggy", "cargos": "pantalon cargo",
    # robes
    "sundress": "robe", "gown": "robe de soirée", "nuisette": "nuisette", "kaftan": "caftan", "caftan": "caftan",
    "dresses": "robe", "skirts": "jupe", "robes": "robe",
    # nuit, bain, lingerie
    "bra": "soutien-gorge", "string": "string", "boxer": "boxer", "calecon": "caleçon", "slip": "slip",
    "peignoir": "peignoir", "pyjamas": "pyjama", "swimsuit": "maillot de bain", "trikini": "trikini",
    "boardshort": "short de bain", "pareo": "paréo", "lingerie": "lingerie", "brassieres": "brassière",
    # chaussures
    "tennis": "baskets", "derby": "derbies", "richelieu": "richelieus", "richelieus": "richelieus",
    "loafers": "mocassins", "loafer": "mocassins", "mocassin": "mocassins", "rangers": "rangers",
    "santiags": "santiags", "santiag": "santiags", "cuissardes": "cuissardes", "bottillons": "bottines",
    "bottine": "bottines", "botte": "bottes", "talons": "talons", "heels": "talons", "pumps": "escarpins",
    "escarpin": "escarpins", "stiletto": "escarpins", "compensees": "compensées", "wedges": "compensées",
    "sabots": "sabots", "clogs": "sabots", "claquettes": "claquettes", "slides": "claquettes",
    "sandals": "sandales", "sandale": "sandales", "chaussons": "chaussons", "pantoufles": "chaussons",
    "slippers": "chaussons", "babies": "babies", "spartiates": "spartiates", "mule": "mules",
    "shoes": "chaussures", "chaussure": "chaussures", "boot": "boots", "trainer": "baskets",
    "ballerine": "ballerines", "flats": "ballerines", "espadrille": "espadrilles", "tong": "tongs",
    "crampons": "chaussures de foot", "cleats": "chaussures de foot", "creepers": "creepers",
    # sacs et petite maroquinerie
    "bandouliere": "sac bandoulière", "crossbody": "sac bandoulière", "besace": "besace", "cartable": "cartable",
    "sacoche": "sacoche", "backpack": "sac à dos", "handbag": "sac à main", "clutch": "pochette",
    "shopper": "cabas", "valise": "valise", "trousse": "trousse", "wallet": "portefeuille",
    "cardholder": "porte-cartes", "purse": "sac à main", "bags": "sac", "sacs": "sac", "minaudiere": "pochette",
    "baguette": "sac baguette", "bowling": "sac bowling", "hobo": "sac hobo", "satchel": "cartable",
    # accessoires
    "foulard": "foulard", "scarf": "écharpe", "snood": "snood", "chapeau": "chapeau", "hat": "chapeau",
    "beanie": "bonnet", "cap": "casquette", "beret": "béret", "bandana": "bandana", "bandeau": "bandeau",
    "headband": "bandeau", "chouchou": "chouchou", "scrunchie": "chouchou", "barrette": "barrette",
    "cravate": "cravate", "bretelles": "bretelles", "belt": "ceinture", "gloves": "gants", "gant": "gants",
    "mitaines": "mitaines", "moufles": "moufles", "sunglasses": "lunettes de soleil", "watch": "montre",
    "bijou": "bijou", "bijoux": "bijou", "collier": "collier", "necklace": "collier", "bracelet": "bracelet",
    "bague": "bague", "earrings": "boucles d'oreilles", "pendentif": "pendentif", "broche": "broche",
    "parapluie": "parapluie", "socks": "chaussettes", "chaussette": "chaussettes", "cagoule": "cagoule",
    "balaclava": "cagoule", "chapka": "chapka", "fedora": "chapeau", "panama": "chapeau", "visiere": "visière",
    "casquettes": "casquette", "bonnets": "bonnet", "echarpes": "écharpe", "lunette": "lunettes",
    # bébé et enfant
    "grenouillere": "grenouillère", "gigoteuse": "gigoteuse", "bavoir": "bavoir", "ensemble": "ensemble",
    "layette": "layette", "bloomer": "bloomer",
})
# Les titres tirés d'une adresse perdent souvent les petits mots (« pantalon survetement »,
# « sac dos ») : on ajoute aussi chaque expression sans ces petits mots.
for _k, _v in list(TYPES.items()):
    _short = " ".join(w for w in _k.split() if w not in {"de", "a", "d'", "d", "du", "en", "la", "le", "des"})
    if " " in _short and _short not in TYPES:
        TYPES[_short] = _v
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
        diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        # une lettre changée, ou deux lettres voisines inversées (adidsa → adidas)
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1
                                  and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    if len(a) > len(b):
        a, b = b, a
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


# Mots courants des annonces qui ressemblent à un mot connu mais ne doivent jamais être « corrigés ».
KEEP = {"taille", "tailles", "haute", "hautes", "bonne", "bonnes", "saison", "boost", "basse", "large",
        "longue", "longues", "courte", "courtes", "porte", "portee", "poche", "poches", "neuve", "mixte",
        "droite", "petite", "grande", "moyenne", "classe", "slime", "court", "toile", "ville", "plage"}
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
    if len(w) < 5 or w in vocab or w.rstrip("s") in vocab or w in KEEP:
        return w
    matches = sorted(v for v in vocab if len(v) >= 5 and _close(w, v))
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
