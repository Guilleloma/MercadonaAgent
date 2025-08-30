from __future__ import annotations

from mercadona_agent.application.menu_service import MenuService
from mercadona_agent.domain.menu import MenuWeek, MenuDay, Recipe, Ingredient


def test_expand_scales_servings_and_formats_units():
    menu = MenuWeek(
        days=[
            MenuDay(
                day="lunes",
                recipes=[
                    Recipe(
                        name="Prueba",
                        servings=2,
                        ingredients=[
                            Ingredient(name="arroz", quantity=500, unit="g"),
                            Ingredient(name="leche", quantity=1, unit="l"),
                            Ingredient(name="huevos", quantity=2, unit="ud"),
                        ],
                    )
                ],
            )
        ]
    )

    svc = MenuService()
    items = svc.expand_to_items(menu, target_servings=4)  # x2
    by_name = {it.name: it for it in items}

    assert by_name["arroz"].unit in {"g", "kg"}
    # 500g x2 = 1000g -> 1 kg
    assert by_name["arroz"].unit == "kg"
    assert by_name["arroz"].quantity == 1.0

    # 1l x2 = 2l
    assert by_name["leche"].unit == "l"
    assert by_name["leche"].quantity == 2.0

    # 2ud x2 = 4ud
    assert by_name["huevos"].unit == "ud"
    assert by_name["huevos"].quantity == 4


def test_expand_consolidates_same_name_across_recipes_and_units():
    menu = MenuWeek(
        days=[
            MenuDay(
                day="martes",
                recipes=[
                    Recipe(
                        name="Receta1",
                        servings=2,
                        ingredients=[Ingredient(name="leche", quantity=500, unit="ml")],
                    ),
                    Recipe(
                        name="Receta2",
                        servings=2,
                        ingredients=[Ingredient(name="leche", quantity=0.6, unit="l")],
                    ),
                ],
            )
        ]
    )

    svc = MenuService()
    items = svc.expand_to_items(menu)
    by_name = {it.name: it for it in items}

    # 500ml + 0.6l = 500ml + 600ml = 1100ml -> 1.1l
    assert by_name["leche"].unit == "l"
    assert abs(by_name["leche"].quantity - 1.1) < 1e-6
