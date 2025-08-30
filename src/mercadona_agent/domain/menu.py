from __future__ import annotations

from typing import ClassVar, List, Optional
from pydantic import BaseModel, Field, field_validator

from mercadona_agent.domain.models import Item


class Ingredient(BaseModel):
    name: str = Field(..., min_length=1)
    quantity: float = Field(gt=0.0)
    unit: str = Field(...)

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        u = v.strip().lower()
        if u in {"unidad", "unid", "u"}:
            u = "ud"
        if u not in Item.ALLOWED_UNITS:
            raise ValueError(f"Unidad no permitida en Ingredient: {u}")
        return u


class Recipe(BaseModel):
    name: str = Field(..., min_length=1)
    servings: int = Field(gt=0, default=2)
    ingredients: List[Ingredient] = Field(default_factory=list)


class MenuDay(BaseModel):
    day: str = Field(..., min_length=1)
    recipes: List[Recipe] = Field(default_factory=list)


class MenuWeek(BaseModel):
    days: List[MenuDay] = Field(default_factory=list)

    def all_recipes(self) -> List[Recipe]:
        out: list[Recipe] = []
        for d in self.days:
            out.extend(d.recipes)
        return out
