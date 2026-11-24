"""Site web de l'agent Vinted.

Lancer en local :  uvicorn web.app:app --reload   (depuis le dossier vinted-agent)
"""
from __future__ import annotations

import os
import sys
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vinted_agent.identify import describe_image, item_from_url  # noqa: E402
from vinted_agent.links import search_links  # noqa: E402
from vinted_agent.gemini import QuotaExceeded, describe_image_gemini, gemini_enabled  # noqa: E402
from vinted_agent.links import search_url  # noqa: E402
from vinted_agent.similar import similar  # noqa: E402
from vinted_agent.sites import ebay_enabled, ebay_url, site_results  # noqa: E402

STATIC = Path(__file__).parent / "static"
MAX_PHOTO_BYTES = 6_000_000
PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Limites anti-abus (réglables par variables d'environnement)
PER_IP_PER_HOUR = int(os.environ.get("PER_IP_PER_HOUR", "20"))
CLAUDE_PER_DAY = int(os.environ.get("CLAUDE_PER_DAY", "300"))  # plafond global = plafond de dépense
TRUST_PROXY = os.environ.get("TRUST_PROXY", "1") == "1"  # Render, Railway… passent l'IP réelle

app = FastAPI(title="Agent Vinted", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

_hits: dict[str, deque] = defaultdict(deque)
_claude_calls: deque = deque()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if TRUST_PROXY and fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def _rate_limit(ip: str) -> None:
    now = time.time()
    q = _hits[ip]
    while q and q[0] < now - 3600:
        q.popleft()
    if len(q) >= PER_IP_PER_HOUR:
        raise HTTPException(429, "Trop de recherches. Réessaie dans un moment.")
    q.append(now)


def _claude_available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    now = time.time()
    while _claude_calls and _claude_calls[0] < now - 86400:
        _claude_calls.popleft()
    return len(_claude_calls) < CLAUDE_PER_DAY


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "photos": bool(os.environ.get("ANTHROPIC_API_KEY")) or gemini_enabled(), "ebay": ebay_enabled()}


@app.post("/api/identify")
async def identify(
    request: Request,
    url: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    size: Optional[str] = Form(None),
    max_price: Optional[float] = Form(None),
    country: str = Form("fr"),
):
    _rate_limit(_client_ip(request))
    size = (size or "").strip()[:20] or None
    if max_price is not None and not (0 < max_price < 100_000):
        max_price = None

    try:
        if photo is not None and photo.filename:
            if photo.content_type not in PHOTO_TYPES:
                raise HTTPException(400, "Format de photo non pris en charge (JPEG, PNG, WebP).")
            data = await photo.read(MAX_PHOTO_BYTES + 1)
            if len(data) > MAX_PHOTO_BYTES:
                raise HTTPException(400, "Photo trop lourde (6 Mo maximum).")
            if _claude_available():
                _claude_calls.append(time.time())
                item = describe_image(image_bytes=data, media_type=photo.content_type)
            elif gemini_enabled():
                try:
                    item = await run_in_threadpool(describe_image_gemini, data, photo.content_type)
                except QuotaExceeded:
                    raise HTTPException(503, "La reconnaissance de photos a atteint sa limite gratuite du jour. "
                                             "Réessaie demain, ou colle un lien.")
            else:
                raise HTTPException(503, "L'analyse de photos est indisponible pour le moment. Essaie avec un lien.")
        elif url:
            use_claude = _claude_available()
            if use_claude:
                _claude_calls.append(time.time())
            item = item_from_url(url.strip(), use_claude=use_claude)
        else:
            raise HTTPException(400, "Envoie un lien ou une photo.")
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(502, "Impossible d'analyser cet article. Essaie un autre lien ou une autre photo.")

    if size:
        item.size = size
    if not item.queries:
        raise HTTPException(422, "Je n'ai pas reconnu l'article. Essaie une photo plus nette.")
    sim = similar(item)
    if sim:
        sim["sites"] = await run_in_threadpool(site_results, sim["query"], max_price, country)
        for b in sim["brands"]:
            b["vinted_url"] = search_url(b["query"], max_price, country=country)
            b["ebay_url"] = ebay_url(b["query"], max_price, country)
    return {
        "item": item.model_dump(exclude={"queries"}),
        "similar": sim,
        "links": search_links(item, size=size, max_price=max_price, country=country),
        "sites": await run_in_threadpool(site_results, item.queries[0], max_price, country),
        "sites_query": item.queries[0],
    }
