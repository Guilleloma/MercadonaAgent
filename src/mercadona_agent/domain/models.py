from __future__ import annotations

from typing import List, Optional, ClassVar
from pydantic import BaseModel, Field, field_validator


class Item(BaseModel):
    ALLOWED_UNITS: ClassVar[set[str]] = {"ud", "kg", "g", "l", "ml", "pack"}

    name: str = Field(..., min_length=1)
    quantity: float = Field(gt=0.0, default=1.0)
    unit: str = Field(default="ud")  # ud, kg, g, l, ml, pack, etc.
    category: Optional[str] = None  # frescos, despensa, bebidas, limpieza, etc.
    notes: Optional[str] = None

    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, v: str) -> str:
        u = v.strip().lower()
        # normalizaciones simples
        if u in {"unidad", "unid", "u"}:
            u = "ud"
        if u not in cls.ALLOWED_UNITS:
            raise ValueError(f"Unidad no permitida: {u}. Permitidas: {sorted(cls.ALLOWED_UNITS)}")
        return u

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("category")
    @classmethod
    def normalize_category(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.strip().lower()


class ShoppingList(BaseModel):
    items: List[Item] = Field(default_factory=list)

    def add_item(self, item: Item) -> None:
        self.items.append(item)

    def list_by_category(self) -> dict[str, list[Item]]:
        grouped: dict[str, list[Item]] = {}
        for it in self.items:
            key = it.category or "otros"
            grouped.setdefault(key, []).append(it)
        return grouped

    def deduplicate(self) -> None:
        # Simple de-duplication by (name, unit, category); sums quantities
        index: dict[tuple[str, str, str], Item] = {}
        new_items: list[Item] = []
        for it in self.items:
            key = (it.name.lower(), it.unit, (it.category or ""))
            if key in index:
                idx_item = index[key]
                idx_item.quantity += it.quantity
            else:
                index[key] = it
                new_items.append(it)
        self.items = new_items
