"""Identifier le vêtement à partir d'un lien produit ou d'une photo."""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import ipaddress
import re
import socket
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .models import Item

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

CLAUDE_MODEL = os.environ.get("VINTED_AGENT_MODEL", "claude-opus-5-5")

PROMPT = (
    "Tu aides à retrouver ce vêtement d'occasion sur Vinted. "
    "Identifie la marque, le modèle, le type de vêtement, la couleur principale (en français) "
    "et la taille si elle est visible. Puis propose 2 ou 3 requêtes de recherche Vinted "
    "courtes (comme un humain les taperait), de la plus précise à la plus large, "
    "par exemple 'nike air force 1 blanche' puis 'nike air force 1' puis 'baskets nike blanches'. "
    "Laisse un champ vide si tu n'es pas sûr, n'invente pas."
)


# ---------- Lien produit ----------

MAX_PAGE_BYTES = 5_000_000


def _check_public_url(url: str) -> None:
    """Refuse les adresses internes (le site est public : on ne doit pas pouvoir
    lui faire lire le réseau du serveur)."""
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError("Lien invalide : il doit commencer par http:// ou https://")
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80))
    except socket.gaierror:
        raise ValueError("Site introuvable.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ValueError("Ce lien n'est pas autorisé.")


def safe_get(url: str) -> str:
    """Télécharge une page publique en suivant au plus 5 redirections, taille limitée."""
    for _ in range(6):
        _check_public_url(url)
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=False, stream=True)
        if resp.is_redirect:
            url = urljoin(url, resp.headers.get("Location", ""))
            continue
        resp.raise_for_status()
        chunks, size = [], 0
        for chunk in resp.iter_content(65536):
            size += len(chunk)
            if size > MAX_PAGE_BYTES:
                raise ValueError("Page trop lourde.")
            chunks.append(chunk)
        resp.encoding = resp.encoding or "utf-8"
        return b"".join(chunks).decode(resp.encoding, errors="replace")
    raise ValueError("Trop de redirections.")

def _first(*values):
    for v in values:
        if v:
            return v
    return None


def _jsonld_product(soup: BeautifulSoup) -> Optional[dict]:
    """Cherche un bloc JSON-LD de type Product (présent sur la plupart des e-shops)."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                t = node.get("@type")
                if t == "Product" or (isinstance(t, list) and "Product" in t):
                    return node
                stack.extend(node.get("@graph", []) if isinstance(node.get("@graph"), list) else [])
            elif isinstance(node, list):
                stack.extend(node)
    return None


def _meta(soup: BeautifulSoup, prop: str) -> Optional[str]:
    tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
    return tag.get("content") if tag else None


def item_from_url_slug(url: str) -> Item:
    """Devine l'article à partir des mots de l'adresse (quand le site bloque la lecture de la page)."""
    path = urlparse(url).path
    words, raw = [], []
    for part in re.split(r"[/\-_.+]+", path.lower()):
        if part and not (re.search(r"\d", part) and not re.fullmatch(r"\d{1,2}", part)):
            raw.append(part)
        if not part or part in ("p", "fr", "en", "produit", "product", "products", "html", "htm", "www", "a", "de",
                                "du", "la", "le", "les", "en", "et", "pour", "avec", "the", "and", "with"):
            continue
        if re.search(r"\d", part) and not re.fullmatch(r"\d{1,2}", part):
            continue  # références et identifiants (lz5579, 518585…)
        words.append(part)
    text = " ".join(words)
    if len(words) < 2:
        raise ValueError("Ce site bloque la lecture de sa page. Essaie avec une photo de l'article.")
    from .similar import _plain, describe, known_brands  # import ici pour éviter une boucle d'imports
    host = urlparse(url).hostname or ""
    raw_text = " ".join(raw)
    found = next((b for b in known_brands() if re.search(rf"(^| ){re.escape(_plain(b))}( |$)", raw_text)), None) \
        or next((b for b in known_brands() if re.sub(r"[^a-z]", "", _plain(b)) in host.split(".")), None)
    brand = _plain(found) if found else None
    item = Item(brand=found, model=" ".join(words).capitalize())
    d = describe(item)
    if brand:
        rest = [w for w in words if w not in brand.split()]
        queries = [" ".join([brand] + rest[:7])]
    else:
        queries = [" ".join(words[:8])]
    short = " ".join(x for x in (brand, d["type"], d["color"]) if x)
    if d["type"] and short != queries[0]:
        queries.append(short)
    item.queries = list(dict.fromkeys(queries))
    return item


def item_from_url(url: str, use_claude: bool = True) -> Item:
    try:
        html = safe_get(url)
    except ValueError:
        raise
    except Exception as e:  # site qui bloque les serveurs (403), page absente, délai dépassé…
        print(f"Page illisible ({e}), repli sur l'adresse.", flush=True)
        return item_from_url_slug(url)
    soup = BeautifulSoup(html, "html.parser")
    product = _jsonld_product(soup) or {}

    brand = product.get("brand")
    if isinstance(brand, dict):
        brand = brand.get("name")
    if isinstance(brand, list):
        brand = brand[0].get("name") if brand and isinstance(brand[0], dict) else None

    image = product.get("image")
    if isinstance(image, list):
        image = image[0] if image else None
    if isinstance(image, dict):
        image = image.get("url")

    offers = product.get("offers")
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    price = None
    if isinstance(offers, dict):
        try:
            price = float(str(_first(offers.get("price"), offers.get("lowPrice"))).replace(",", "."))
        except (TypeError, ValueError):
            price = None

    title = _first(product.get("name"), _meta(soup, "og:title"), soup.title.string if soup.title else None)
    title = (title or "").strip()
    color = product.get("color") if isinstance(product.get("color"), str) else None

    item = Item(
        brand=brand,
        model=title or None,
        color=color,
        retail_price=price,
        image_url=_first(image, _meta(soup, "og:image")),
    )

    if use_claude and os.environ.get("ANTHROPIC_API_KEY") and item.image_url:
        # La photo + le titre donnent de bien meilleures requêtes que le titre seul.
        try:
            enriched = describe_image(
                image_url=item.image_url,
                hint=f"Titre de la page produit : {title}. Marque indiquée : {brand or 'inconnue'}.",
            )
            item = enriched.model_copy(update={
                "brand": item.brand or enriched.brand,
                "retail_price": item.retail_price,
                "image_url": item.image_url,
            })
        except Exception as e:  # on garde le résultat sans Claude
            print(f"(Analyse Claude ignorée : {e})")

    if not item.queries:
        item.queries = _queries_from_title(title, brand)
    return item


def _queries_from_title(title: str, brand: Optional[str]) -> list[str]:
    # Retire le bruit fréquent des titres de pages produit
    clean = re.split(r"[|\-–—]\s", title)[0]
    clean = re.sub(r"\b(homme|femme|unisexe|men|women|achat|acheter)\b", "", clean, flags=re.I)
    clean = re.sub(r"['’]\d{2}\b", "", clean)  # ex. Air Force 1 '07
    clean = re.sub(r"\s+", " ", clean).strip()
    queries = [clean.lower()]
    if brand and brand.lower() not in clean.lower():
        queries.insert(0, f"{brand} {clean}".lower())
    words = clean.split()
    if len(words) > 3:
        queries.append(" ".join(words[:3]).lower())
    return list(dict.fromkeys(q for q in queries if q))


# ---------- Photo ----------

def describe_image(image_path: Optional[str] = None, image_url: Optional[str] = None,
                   hint: str = "", image_bytes: Optional[bytes] = None,
                   media_type: str = "image/jpeg") -> Item:
    import anthropic

    if image_bytes:
        data = base64.standard_b64encode(image_bytes).decode("utf-8")
        source = {"type": "base64", "media_type": media_type, "data": data}
    elif image_path:
        data = base64.standard_b64encode(Path(image_path).read_bytes()).decode("utf-8")
        media_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
        source = {"type": "base64", "media_type": media_type, "data": data}
    elif image_url:
        source = {"type": "url", "url": image_url}
    else:
        raise ValueError("Il faut une image (fichier ou URL).")

    client = anthropic.Anthropic()
    response = client.messages.parse(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": source},
                {"type": "text", "text": PROMPT + (f"\n\nIndice : {hint}" if hint else "")},
            ],
        }],
        output_format=Item,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError("Claude n'a pas pu analyser cette image.")
    item = response.parsed_output
    if image_url:
        item.image_url = image_url
    return item


def item_from_photo(path: str) -> Item:
    return describe_image(image_path=path)
