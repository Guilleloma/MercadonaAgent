from mercadona_agent.domain.models import Item, ShoppingList
from mercadona_agent.application.services import ListService


def test_deduplicate_items():
    s = ListService()
    s.add_items([
        Item(name="Leche entera", quantity=1, unit="ud", category="despensa"),
        Item(name="Leche entera", quantity=2, unit="ud", category="despensa"),
    ])
    sl = s.current
    assert len(sl.items) == 1
    assert sl.items[0].quantity == 3


def test_group_by_category():
    sl = ShoppingList(items=[
        Item(name="Manzana", quantity=1, unit="kg", category="frescos"),
        Item(name="Arroz", quantity=1, unit="kg", category="despensa"),
    ])
    grouped = sl.list_by_category()
    assert set(grouped.keys()) == {"frescos", "despensa"}
