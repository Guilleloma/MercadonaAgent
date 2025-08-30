from __future__ import annotations

from typing import Protocol
from mercadona_agent.domain.product import Product


class ProductSearchPort(Protocol):
    def search_best(self, *, name: str, quantity: float, unit: str) -> Product | None:
        """Return best matching product (or None)."""
        ...
