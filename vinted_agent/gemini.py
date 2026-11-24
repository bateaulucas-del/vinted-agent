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

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "brand": {"type": "STRING", "nullable": True},
        "model": {"type": "STRING", "nullable": True},
        "category": {"type": "STRING", "nullable": True},
        "color": {"type": "STRING", "nullable": True},
        "size": {"type": "STRING", "nullable": True},
        "queries": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["queries"],
}


class QuotaExceeded(RuntimeError):
    pass


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
    r = requests.post(URL.format(model=GEMINI_MODEL), json=body, timeout=40,
                      headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    if r.status_code == 429:
        raise QuotaExceeded("Quota Gemini du jour épuisé.")
    r.raise_for_status()
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
