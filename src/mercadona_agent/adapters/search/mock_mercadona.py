from __future__ import annotations

from urllib.parse import quote_plus
from mercadona_agent.domain.product import Product
from mercadona_agent.ports.product_search import ProductSearchPort


class MockMercadonaSearchAdapter(ProductSearchPort):
    BASE = "https://tienda.mercadona.es/search-results?query="

    def search_best(self, *, name: str, quantity: float, unit: str) -> Product | None:
        # Demo: build a search URL using name + unit
        query = f"{name} {quantity}{unit}".strip()
        url = f"{self.BASE}{quote_plus(query)}"
        return Product(name=name, url=url, price=None, unit=unit, size=None, match_score=0.5)
