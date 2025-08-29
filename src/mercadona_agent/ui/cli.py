from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from mercadona_agent.application.services import ListService
from mercadona_agent.domain.models import Item
from mercadona_agent.adapters.persistence.json_repo import JSONShoppingListRepository
from mercadona_agent.application.importers import parse_lines
from pydantic import ValidationError

app = typer.Typer(help="Mercadona Agent CLI - Iteración I1 (generador de lista)")
console = Console()
repo = JSONShoppingListRepository()
service = ListService(repo.load())


@app.command()
def add(
    name: str = typer.Argument(..., help="Nombre del producto, p.ej. 'leche entera'"),
    quantity: float = typer.Option(1.0, "--qty", "-q", help="Cantidad"),
    unit: str = typer.Option("ud", "--unit", "-u", help="Unidad: ud|kg|g|l|ml|pack"),
    category: Optional[str] = typer.Option(None, "--cat", help="Categoría: frescos|despensa|...")
):
    """Añade un ítem a la lista actual (se consolidan duplicados)."""
    try:
        item = Item(name=name, quantity=quantity, unit=unit, category=category)
    except ValidationError as e:
        console.print(f"[red]Error de validación:[/red] {e}")
        raise typer.Exit(code=1)
    service.add_items([item], deduplicate=True)
    repo.save(service.current)
    console.print("[green]Añadido y guardado[/green]")


@app.command()
def show():
    """Muestra la lista actual agrupada por categoría."""
    sl = service.current
    table = Table(title="Lista de la compra")
    table.add_column("Categoría")
    table.add_column("Nombre")
    table.add_column("Cantidad")
    table.add_column("Unidad")

    for cat, items in sl.list_by_category().items():
        for it in items:
            table.add_row(cat, it.name, f"{it.quantity}", it.unit)
    console.print(table)


@app.command()
def export_json(path: str = typer.Argument("data/shopping_list.json")):
    """Exporta la lista a JSON (ruta configurable)."""
    repo.save(service.current, path=path)
    console.print(f"[green]Exportado a {path}[/green]")


@app.command()
def import_json(path: str = typer.Argument("data/shopping_list.json")):
    """Importa la lista desde JSON (ruta configurable)."""
    loaded = repo.load(path=path)
    global service
    service = ListService(loaded)
    console.print(f"[green]Importado desde {path}[/green]")


@app.command("bulk-import")
def bulk_import(
    path: str = typer.Argument(..., help="Ruta a archivo .txt o .csv con items"),
    delimiter: str = typer.Option(",", "--delim", help="Delimitador si CSV"),
    has_header: bool = typer.Option(False, "--header", help="Indica si la primera línea es cabecera"),
):
    """Importa múltiples ítems desde un archivo.

    Formatos admitidos por línea:
    - name,quantity,unit,category
    - name;quantity;unit;category (usar --delim ";")
    - name  (defaults: qty=1, unit=ud, category=None)
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        items = parse_lines(lines, delimiter=delimiter, has_header=has_header)
    except FileNotFoundError:
        console.print(f"[red]Archivo no encontrado:[/red] {path}")
        raise typer.Exit(code=1)
    except ValidationError as e:
        console.print(f"[red]Error de validación:[/red] {e}")
        raise typer.Exit(code=1)

    service.add_items(items, deduplicate=True)
    repo.save(service.current)
    console.print(f"[green]Importados {len(items)} ítems y guardado[/green]")


if __name__ == "__main__":
    app()
