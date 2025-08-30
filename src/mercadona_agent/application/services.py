from __future__ import annotations

from typing import Iterable
from mercadona_agent.domain.models import Item, ShoppingList


class ListService:
    """Application service to manage shopping lists.

    Keeps domain logic here, independent from persistence/UI.
    """

    def __init__(self, shopping_list: ShoppingList | None = None) -> None:
        self._list = shopping_list or ShoppingList()

    @property
    def current(self) -> ShoppingList:
        return self._list

    def clear(self) -> None:
        """Reset current shopping list."""
        self._list = ShoppingList()

    def add_items(self, items: Iterable[Item], deduplicate: bool = True) -> None:
        for item in items:
            self._list.add_item(item)
        if deduplicate:
            self._list.deduplicate()
