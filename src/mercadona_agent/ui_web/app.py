from __future__ import annotations

from pathlib import Path
from typing import Optional
import json
import os

from fastapi import FastAPI, Request, Form
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from mercadona_agent.adapters.persistence.json_repo import JSONShoppingListRepository
from mercadona_agent.application.services import ListService
from mercadona_agent.domain.models import Item
from mercadona_agent.application.menu_service import MenuService
from mercadona_agent.domain.menu import MenuWeek
from mercadona_agent.adapters.search.mock_mercadona import MockMercadonaSearchAdapter
from mercadona_agent.application.search_agent import SearchAgentService
from mercadona_agent.application.product_mapper import map_urls_to_list
from mercadona_agent.application.cart_automation import CartAutomationService

# Cargar variables de entorno
load_dotenv()

# Instancias de aplicación/servicios
repo = JSONShoppingListRepository()
service = ListService(repo.load())
menu_service = MenuService()
search_adapter = MockMercadonaSearchAdapter()
agent = SearchAgentService(search_adapter)

# Config de automatización desde entorno
POSTAL_CODE = os.getenv("MRC_POSTAL_CODE") or os.getenv("POSTAL_CODE")
HEADLESS = os.getenv("MRC_AUTOMATION_HEADLESS", "false").strip().lower() in {"1","true","yes","y","on"}
KEEP_OPEN = int(os.getenv("MRC_AUTOMATION_KEEP_OPEN_SECONDS", "8"))
SLOW_MO_MS = int(os.getenv("MRC_AUTOMATION_SLOW_MO_MS", "0"))
STORAGE_PATH = os.getenv("MRC_AUTOMATION_STORAGE", "data/playwright_state.json")

automation = CartAutomationService(
    headless=HEADLESS,
    slow_mo=SLOW_MO_MS,
    postal_code=POSTAL_CODE,
    storage_path=STORAGE_PATH,
    keep_open_seconds=KEEP_OPEN,
)

# FastAPI + Templates
app = FastAPI(title="MercadonaAgent Web")

# Plantillas dentro del paquete
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, msg: Optional[str] = None, err: Optional[str] = None):
    grouped = service.current.list_by_category()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "grouped": grouped,
            "msg": msg,
            "err": err,
        },
    )


@app.get("/menu", response_class=HTMLResponse)
async def menu_page(request: Request, msg: Optional[str] = None, err: Optional[str] = None):
    sample = {
        "days": [
            {
                "day": "lunes",
                "recipes": [
                    {
                        "name": "Ensalada de pollo",
                        "servings": 2,
                        "ingredients": [
                            {"name": "pechuga de pollo", "quantity": 300, "unit": "g"},
                            {"name": "lechuga", "quantity": 1, "unit": "ud"},
                            {"name": "tomate", "quantity": 2, "unit": "ud"}
                        ]
                    }
                ]
            }
        ]
    }
    return templates.TemplateResponse(
        "menu.html",
        {"request": request, "sample_json": json.dumps(sample, ensure_ascii=False, indent=2), "msg": msg, "err": err},
    )


@app.post("/add")
async def add(
    name: str = Form(...),
    quantity: float = Form(1.0),
    unit: str = Form("ud"),
    category: Optional[str] = Form(None),
):
    try:
        item = Item(name=name, quantity=quantity, unit=unit, category=category)
        service.add_items([item], deduplicate=True)
        repo.save(service.current)
        return RedirectResponse(url="/?msg=Item%20añadido", status_code=303)
    except Exception as e:  # incluye ValidationError
        return RedirectResponse(url=f"/?err={str(e)}", status_code=303)


@app.post("/map-urls")
async def map_urls(urls_text: str = Form(...)):
    try:
        urls = [ln.strip() for ln in urls_text.splitlines() if ln.strip()]
        count = map_urls_to_list(urls, service.current)
        repo.save(service.current)
        return RedirectResponse(url=f"/?msg=Mapeados%20{count}%20productos", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/?err={str(e)}", status_code=303)


@app.post("/cart/add-by-urls")
async def cart_add_by_urls(
    urls_text: str = Form(""),
    slow_mo_ms: Optional[str] = Form(None),
    keep_open_s: Optional[str] = Form(None),
    keep_open_forever: Optional[str] = Form(None),
    api_first: Optional[str] = Form(None),
    clear_cart: Optional[str] = Form(None),
):
    try:
        urls = [ln.strip() for ln in urls_text.splitlines() if ln.strip()]
        if not urls:
            urls = [it.product_url for it in service.current.items if it.product_url]
        if not urls:
            return RedirectResponse(url="/?err=No%20hay%20URLs%20de%20producto", status_code=303)
        # Overrides temporales
        ov_slow: Optional[int] = None
        ov_keep: Optional[int] = None
        if slow_mo_ms and str(slow_mo_ms).strip():
            ov_slow = int(str(slow_mo_ms).strip())
        if keep_open_s and str(keep_open_s).strip():
            ov_keep = int(str(keep_open_s).strip())
        # Flags
        def _to_bool(v: Optional[str]) -> bool:
            return bool(v and str(v).strip().lower() in {"1", "true", "yes", "y", "on"})
        flag_api = _to_bool(api_first)
        flag_clear = _to_bool(clear_cart)
        flag_forever = _to_bool(keep_open_forever)
        temp_automation = CartAutomationService(
            headless=HEADLESS,
            slow_mo=ov_slow if ov_slow is not None else SLOW_MO_MS,
            postal_code=POSTAL_CODE,
            storage_path=STORAGE_PATH,
            keep_open_seconds=ov_keep if ov_keep is not None else KEEP_OPEN,
            keep_open_forever=flag_forever,
        )
        # Ejecutar: si ventana permanente, lanzar en background y devolver inmediatamente
        if flag_forever:
            import threading
            def _run_bg():
                try:
                    temp_automation.add_by_urls(urls, flag_api, flag_clear)
                except Exception:
                    pass
            threading.Thread(target=_run_bg, daemon=True).start()
            return RedirectResponse(url=f"/?msg=Ejecutando%20en%20segundo%20plano%20(con%20ventana%20abierta%20hasta%20cerrar)", status_code=303)
        else:
            # Ejecutar Playwright (sincrono) fuera del loop async
            results = await run_in_threadpool(temp_automation.add_by_urls, urls, flag_api, flag_clear)
            added = sum(1 for v in results.values() if v == "added")
            errors = sum(1 for v in results.values() if v != "added")
            return RedirectResponse(url=f"/?msg=Carro:%20{added}%20añadidos,%20{errors}%20errores", status_code=303)
    except RuntimeError as e:
        return RedirectResponse(url=f"/?err={str(e)}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/?err={str(e)}", status_code=303)


@app.post("/cart/setup-session")
async def cart_setup_session(keep_seconds: Optional[str] = Form(None)):
    try:
        ks_val: Optional[int] = None
        if keep_seconds and str(keep_seconds).strip():
            ks_val = int(str(keep_seconds).strip())
        await run_in_threadpool(automation.setup_session, ks_val)
        return RedirectResponse(url="/?msg=Sesión%20configurada", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/?err={str(e)}", status_code=303)


@app.get("/cart/last-results.json")
async def cart_last_results_json():
    try:
        p = Path("data/last_cart_results.json")
        if not p.exists():
            return JSONResponse({"error": "No hay resultados previos"}, status_code=404)
        import json as _json
        data = _json.loads(p.read_text(encoding="utf-8"))
        return JSONResponse(data)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/clear")
async def clear_list():
    service.clear()
    repo.save(service.current)
    return RedirectResponse(url="/?msg=Lista%20vaciada", status_code=303)


@app.post("/menu/expand")
async def expand_menu(menu_json: str = Form(...), target_servings: Optional[str] = Form(None)):
    try:
        data = json.loads(menu_json)
        menu = MenuWeek(**data)
        ts_val: Optional[int] = None
        if target_servings and str(target_servings).strip():
            ts_val = int(str(target_servings).strip())
        items = menu_service.expand_to_items(menu, target_servings=ts_val)
        service.add_items(items, deduplicate=True)
        repo.save(service.current)
        return RedirectResponse(url=f"/?msg=Generada%20lista%20desde%20menú%20({len(items)}%20items)", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/menu?err={str(e)}", status_code=303)


@app.post("/search-products")
async def search_products():
    try:
        updated = agent.annotate_list(service.current)
        repo.save(service.current)
        return RedirectResponse(url=f"/?msg=Anotados%20{updated}%20productos", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/?err={str(e)}", status_code=303)


    


# Entry point script
def run() -> None:
    import uvicorn

    uvicorn.run("mercadona_agent.ui_web.app:app", host="127.0.0.1", port=8000, reload=False)
