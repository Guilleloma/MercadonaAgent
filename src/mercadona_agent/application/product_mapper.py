from __future__ import annotations

import re
from urllib.parse import urlparse
from typing import Iterable, List, Tuple

from mercadona_agent.domain.models import ShoppingList
from .cart_automation import parse_product_id_from_url


def _slug_tokens(url: str) -> list[str]:
    path = urlparse(url).path
    parts = [p for p in path.split('/') if p]
    slug = parts[-1] if parts else ""
    # keep alnum and hyphens, split by hyphen
    cleaned = re.sub(r"[^a-z0-9\-]+", "-", slug.lower())
    toks = [t for t in cleaned.split('-') if t]
    return toks


def map_urls_to_list(urls: Iterable[str], sl: ShoppingList) -> int:
    """Assign product_url and product_id to best matching items based on slug tokens.

    Strategy: for each URL, compute tokens from the slug and find the item whose
    name contains the most tokens (case-insensitive). Require at least 1 token.
    """
    count = 0
    items = list(sl.items)
    for url in urls:
        toks = _slug_tokens(url)
        if not toks:
            continue
        best_idx = -1
        best_score = 0
        for idx, it in enumerate(items):
            name = it.name.lower()
            score = sum(1 for t in toks if t in name)
            if score > best_score:
                best_score = score
                best_idx = idx
        if best_idx >= 0 and best_score > 0:
            it = items[best_idx]
            it.product_url = url
            pid = parse_product_id_from_url(url)
            if pid is not None:
                it.product_id = pid
            count += 1
    return count
