from __future__ import annotations

from typing import Iterable, List

from pydantic import ValidationError

from mercadona_agent.domain.models import Item


def parse_lines(
    lines: Iterable[str], *, delimiter: str = ",", has_header: bool = False
) -> List[Item]:
    """Parsea líneas de texto (txt/csv) a una lista de Items.

    Formatos por línea admitidos:
    - name,quantity,unit,category
    - name (usa defaults: qty=1, unit=ud)
    - Delimitador configurable; si `has_header=True`, se salta la primera línea.
    """
    items: list[Item] = []
    it = iter(lines)
    if has_header:
        # descartar cabecera
        try:
            next(it)
        except StopIteration:
            return []

    for raw in it:
        line = raw.strip()
        if not line:
            continue
        # permitir líneas simples sin delimitador
        if delimiter not in line:
            name = line
            items.append(Item(name=name, quantity=1, unit="ud"))
            continue
        parts = [p.strip() for p in line.split(delimiter)]
        # normalizar tamaño de partes a 4 como máximo
        if len(parts) == 0:
            continue
        # name obligatorio
        name = parts[0]
        qty = 1.0
        unit = "ud"
        category = None
        if len(parts) > 1 and parts[1] != "":
            try:
                qty = float(parts[1])
            except ValueError as e:
                raise ValidationError.from_exception_data(
                    "Item", [{"type": "value_error", "loc": ("quantity",), "msg": f"Cantidad inválida: {parts[1]}"}]
                ) from e
        if len(parts) > 2 and parts[2] != "":
            unit = parts[2]
        if len(parts) > 3 and parts[3] != "":
            category = parts[3]
        items.append(Item(name=name, quantity=qty, unit=unit, category=category))
    return items
