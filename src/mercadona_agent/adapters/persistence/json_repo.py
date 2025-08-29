from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mercadona_agent.domain.models import Item, ShoppingList
from mercadona_agent.ports.persistence import ShoppingListRepository


class JSONShoppingListRepository(ShoppingListRepository):
    def __init__(self, default_path: str | os.PathLike[str] = "data/shopping_list.json") -> None:
        self.default_path = Path(default_path)
        self.default_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, sl: ShoppingList, *, path: str | None = None) -> None:
        target = Path(path) if path else self.default_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as f:
            json.dump(sl.model_dump(), f, ensure_ascii=False, indent=2)

    def load(self, *, path: str | None = None) -> ShoppingList:
        target = Path(path) if path else self.default_path
        if not target.exists():
            return ShoppingList()
        with target.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        items = [Item(**it) for it in data.get("items", [])]
        return ShoppingList(items=items)
