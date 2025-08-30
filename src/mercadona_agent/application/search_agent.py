from __future__ import annotations

from mercadona_agent.domain.models import ShoppingList
from mercadona_agent.ports.product_search import ProductSearchPort


class SearchAgentService:
    """Agent that enriches shopping list items with best product links.

    Uses a ProductSearchPort implementation (mock or real) to fetch product suggestions
    and writes the URL into each Item.product_url.
    """

    def __init__(self, search_port: ProductSearchPort) -> None:
        self.search_port = search_port

    def annotate_list(self, sl: ShoppingList) -> int:
        updated = 0
        for it in sl.items:
            try:
                best = self.search_port.search_best(name=it.name, quantity=it.quantity, unit=it.unit)
                if best:
                    url_str = str(best.url)
                    # Only persist URLs that point to a product detail page
                    if "/product/" in url_str:
                        it.product_url = url_str
                        if it.notes:
                            # keep existing notes, append
                            it.notes = f"{it.notes} | mercadona"
                        else:
                            it.notes = "mercadona"
                        updated += 1
            except Exception:
                # ignore individual failures to keep agent robust
                continue
        return updated
