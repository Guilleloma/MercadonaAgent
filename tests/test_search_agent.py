from mercadona_agent.domain.models import Item, ShoppingList
from mercadona_agent.application.search_agent import SearchAgentService
from mercadona_agent.adapters.search.mock_mercadona import MockMercadonaSearchAdapter


def test_search_agent_annotates_urls():
    sl = ShoppingList(items=[
        Item(name="pechuga de pollo", quantity=300, unit="g"),
        Item(name="lechuga", quantity=1, unit="ud"),
        Item(name="tomate", quantity=2, unit="ud"),
    ])
    agent = SearchAgentService(MockMercadonaSearchAdapter())

    updated = agent.annotate_list(sl)

    assert updated == 3
    for it in sl.items:
        assert it.product_url and it.product_url.startswith("https://tienda.mercadona.es/")
