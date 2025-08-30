from mercadona_agent.application.product_mapper import map_urls_to_list
from mercadona_agent.domain.models import ShoppingList, Item


def test_map_urls_to_list_assigns_product_ids_and_urls():
    sl = ShoppingList(items=[
        Item(name="Tomate pera", quantity=2, unit="ud"),
        Item(name="Lechuga romana", quantity=1, unit="ud"),
        Item(name="Pechuga de pollo", quantity=1, unit="kg"),
    ])

    urls = [
        "https://tienda.mercadona.es/product/69912/tomate-pera-pieza",
        "https://tienda.mercadona.es/product/69122/lechuga-corazon-romana-paquete",
        "https://tienda.mercadona.es/product/2787/filetes-pechuga-pollo-bandeja",
    ]

    count = map_urls_to_list(urls, sl)

    assert count >= 3
    pid_set = {it.product_id for it in sl.items if it.product_id}
    assert {69912, 69122, 2787}.issubset(pid_set)
    url_set = {it.product_url for it in sl.items if it.product_url}
    for u in urls:
        assert u in url_set
