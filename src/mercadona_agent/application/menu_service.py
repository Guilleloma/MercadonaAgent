from __future__ import annotations

from typing import Dict, Iterable, Tuple

from mercadona_agent.domain.menu import MenuWeek, Recipe, Ingredient
from mercadona_agent.domain.models import Item


class MenuService:
    """Expand and consolidate a MenuWeek into shopping Items.

    - Optionally scale recipes to a target servings count.
    - Convert units to base (g/ml) for consolidation, then format back (kg/l) when large.
    """

    def expand_to_items(self, menu: MenuWeek, *, target_servings: int | None = None) -> list[Item]:
        # aggregate by (name_lower, group) where group in {"g", "ml", "ud", "pack"}
        agg: Dict[Tuple[str, str], float] = {}

        def add(name: str, qty: float, unit: str) -> None:
            key_name = name.strip().lower()
            group, base_qty = self._to_base(unit, qty)
            k = (key_name, group)
            agg[k] = agg.get(k, 0.0) + base_qty

        for day in menu.days:
            for recipe in day.recipes:
                scale = 1.0
                if target_servings is not None and recipe.servings > 0:
                    scale = float(target_servings) / float(recipe.servings)
                for ing in recipe.ingredients:
                    add(ing.name, ing.quantity * scale, ing.unit)

        # materialize Items in pretty units
        items: list[Item] = []
        for (name, group), base_qty in agg.items():
            if group == "g":
                if base_qty >= 1000:
                    items.append(Item(name=name, quantity=base_qty / 1000.0, unit="kg"))
                else:
                    items.append(Item(name=name, quantity=base_qty, unit="g"))
            elif group == "ml":
                if base_qty >= 1000:
                    items.append(Item(name=name, quantity=base_qty / 1000.0, unit="l"))
                else:
                    items.append(Item(name=name, quantity=base_qty, unit="ml"))
            elif group == "ud":
                items.append(Item(name=name, quantity=base_qty, unit="ud"))
            elif group == "pack":
                items.append(Item(name=name, quantity=base_qty, unit="pack"))
            else:
                # fallback as units (shouldn't happen)
                items.append(Item(name=name, quantity=base_qty, unit="ud"))

        return items

    @staticmethod
    def _to_base(unit: str, qty: float) -> tuple[str, float]:
        u = unit.strip().lower()
        if u in {"kg"}:
            return "g", qty * 1000.0
        if u in {"g"}:
            return "g", qty
        if u in {"l"}:
            return "ml", qty * 1000.0
        if u in {"ml"}:
            return "ml", qty
        if u in {"ud", "unidad", "unid", "u"}:
            return "ud", qty
        if u == "pack":
            return "pack", qty
        # Unknown -> treat as units to be safe (Item validator would fail otherwise)
        return "ud", qty
