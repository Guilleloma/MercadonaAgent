from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional


class Product(BaseModel):
    name: str = Field(..., min_length=1)
    url: HttpUrl | str
    price: float | None = None  # total price
    unit: Optional[str] = None  # e.g., "kg", "ud" (display unit)
    size: Optional[str] = None  # e.g., "500 g", "6 ud"
    match_score: float = 0.0
