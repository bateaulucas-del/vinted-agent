"""Reconnaissance de photo avec Gemini (offre gratuite de Google AI Studio).

Clé gratuite à créer sur https://aistudio.google.com/apikey, à mettre dans GEMINI_API_KEY.
Le quota gratuit est limité (nombre de photos par jour, fixé par Google). Quand il est
épuisé, Gemini répond 429 et le site affiche un message clair.
Sur l'offre gratuite, Google peut utiliser les images envoyées pour améliorer ses produits.
"""
from __future__ import annotations

import base64
import json
import os

import requests

from .identify import PROMPT
from .models import Item

# Essayés dans l'ordre : Google renomme souvent ses modèles, on passe au suivant si l'un n'existe plus.
MODELS = [m for m in [os.environ.get("GEMINI_MODEL")] if m] + [
    "gemini-flash-lite-latest", "gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-2.5-flash"]
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "brand": {"type": "STRING"},
        "model": {"type": "STRING"},
        "category": {"type": "STRING"},
        "color": {"type": "STRING"},
        "size": {"type": "STRING"},
        "queries": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["queries"],
}


class QuotaExceeded(RuntimeError):
    pass


class Busy(RuntimeError):
    """Gemini surchargé (erreur 503 côté Google), à réessayer un peu plus tard."""


def gemini_enabled() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def describe_image_gemini(image_bytes: bytes, media_type: str = "image/jpeg") -> Item:
    body = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": media_type, "data": base64.b64encode(image_bytes).decode()}},
            {"text": PROMPT + " Réponds en JSON."},
        ]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA,
                             "temperature": 0.2},
    }
    r = None
    for model in MODELS:
        r = requests.post(URL.format(model=model), json=body, timeout=40,
                          headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        if r.status_code == 429:
            raise QuotaExceeded("Quota Gemini du jour épuisé.")
        if r.status_code == 200:
            break
        print(f"Gemini {model} : erreur {r.status_code} {r.text[:300]}", flush=True)
        if r.status_code not in (400, 404, 500, 503):
            break
    if r is None or r.status_code != 200:
        if r is not None and r.status_code in (500, 503):
            raise Busy("Gemini est surchargé.")
        raise RuntimeError("Gemini indisponible.")
    try:
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(text)
    except (KeyError, IndexError, ValueError) as e:
        raise RuntimeError("Gemini n'a pas pu analyser cette image.") from e
    return Item(
        brand=data.get("brand") or None,
        model=data.get("model") or None,
        category=data.get("category") or None,
        color=data.get("color") or None,
        size=data.get("size") or None,
        queries=[q.strip().lower() for q in data.get("queries", []) if q and q.strip()][:3],
    )
