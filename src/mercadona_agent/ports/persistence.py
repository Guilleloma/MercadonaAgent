from __future__ import annotations

from typing import Protocol
from mercadona_agent.domain.models import ShoppingList


class ShoppingListRepository(Protocol):
    """Port for persistence; allows swapping JSON/DB without changing application code."""

    def save(self, sl: ShoppingList, *, path: str | None = None) -> None:
        ...

    def load(self, *, path: str | None = None) -> ShoppingList:
        ...
