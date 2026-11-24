from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Item(BaseModel):
    """Le vêtement recherché, tel qu'on a pu l'identifier."""

    brand: Optional[str] = Field(None, description="Marque, ex. Nike")
    model: Optional[str] = Field(None, description="Nom du modèle, ex. Air Force 1")
    category: Optional[str] = Field(None, description="Type de vêtement, ex. baskets, sweat, jean")
    color: Optional[str] = Field(None, description="Couleur principale, en français")
    size: Optional[str] = Field(None, description="Taille si connue, ex. M, 42")
    retail_price: Optional[float] = Field(None, description="Prix neuf en euros si connu")
    image_url: Optional[str] = None
    queries: List[str] = Field(
        default_factory=list,
        description="2 à 3 requêtes de recherche Vinted, de la plus précise à la plus large",
    )


class Listing(BaseModel):
    """Une annonce Vinted."""

    id: int
    title: str
    price: float
    currency: str = "EUR"
    brand: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    url: str
    photo_url: Optional[str] = None
    seller: Optional[str] = None
    score: float = 0.0
