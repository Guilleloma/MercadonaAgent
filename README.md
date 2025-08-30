# MercadonaAgent

Agente para generar menú semanal y lista de la compra y preparar el carrito en Mercadona de forma ágil e incremental.

## Propuesta de valor
- __Ahorro de tiempo__: genera la lista a partir de menú/ingredientes y preconfigura el carrito.
- __Menos fricción__: busca equivalencias de productos y presentaciones disponibles.
- __Control__: confirmación humana siempre antes de comprar; transparencia en sustituciones.

## Alcance incremental (roadmap)
- __I0 – Setup & Descubrimiento__
  - Decidir stack, interfaz inicial y alcance del MVP.
  - Investigar API de Mercadona (endpoints, auth, límites, TOS).
  - Definir métricas de éxito.
- __I1 – Generador de lista (sin API)__
  - Input: platos/recetas o lista simple + raciones.
  - Output: lista normalizada (categorías, cantidades, unidades) y validaciones.
  - UI mínima (CLI) + tests.
- __I2 – Búsqueda de productos (read-only)__
  - Mapear ítems de la lista a productos reales (precio, disponibilidad, pack, tienda).
  - Mostrar alternativas y permitir selección manual.
- __I3 – Preparación de carrito (pre-checkout)__
  - Añadir productos seleccionados al carrito de Mercadona.
  - Confirmación explícita del usuario antes de comprar.

## Enfoque Agile y buenas prácticas
- __Iteraciones cortas__: valor demostrable y probado en cada entrega.
- __Documentación viva__: `ITERATIONS.md` registra objetivos, cambios, pruebas y aprendizajes.
- __UX first__: claridad de estados, validaciones, reversibilidad, confirmación previa a acciones críticas.
- __Tests__: unitarios en I1, integración con mocks en I2, e2e controlados en I3.

## Arquitectura (borrador)
- `src/mercadona_agent/domain/`: modelos de dominio (`Item`, `ShoppingList`).
- `src/mercadona_agent/application/`: servicios de aplicación (`ListService`).
- `src/mercadona_agent/ports/`: contratos (persistence, api).
- `src/mercadona_agent/adapters/`: implementaciones (JSON repo, API mercadona).
- `src/mercadona_agent/ui/`: CLI (Typer) y futuras UIs web.
- `tests/`: unit, integration, e2e.

## Control de versiones (GitHub Flow + Conventional Commits)
- __Rama principal__: `master` protegida (revisión, checks verdes, squash merge).
- __Ramas de trabajo__: desde `master` (p. ej. `feature/<scope>-<desc>`, `fix/<id|-desc>`, `docs/…`, `chore/…`).
- __Pull Requests__: 1 review mínima, enlazar iteración/issue, squash merge, CI verde.
- __Commits__: Conventional Commits (`feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`, `chore`).
- __Tags__: semánticos `v0.x.y` al cerrar iteraciones relevantes.

## Setup rápido
Requisitos: Python 3.10+

1) Crear entorno e instalar
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e .[dev]
```

2) Configurar entorno
```
cp .env.example .env
# editar valores si aplica
```

3) Ejecutar CLI
```
mercadona-agent --help
mercadona-agent add "leche entera" -q 2 -u ud --cat despensa
mercadona-agent show
```

4) Tests
```
pytest -q
```

5) UI web (opcional)

Para usar la UI web con automatización del carrito (Playwright):

1. Instala navegadores de Playwright una vez (si no lo hiciste):
   ```
   playwright install chromium
   ```
2. Lanza la web:
   ```
   mercadona-agent-web
   # o: uvicorn mercadona_agent.ui_web.app:app --host 127.0.0.1 --port 8000
   ```
3. En la home:
   - Usa “Configurar sesión (CP/Login)” para guardar estado (cookies/CP/login) en `data/playwright_state.json`.
   - Puedes mapear URLs de producto a ítems, o pegar URLs directamente al añadir.
   - En “Añadir al carro (auto)”, opciones y controles:
     - API-first: intenta añadir vía API interna antes del click en UI (si hay `product_id`).
     - Vaciar carrito antes: intenta vaciar el carrito antes de añadir.
     - Slow Mo (ms): retrasa acciones del navegador para depuración/fiabilidad.
     - Segundos ventana: tiempo que la ventana permanece abierta al finalizar (<= 0 = indefinido si no es headless).
     - Mantener abierto indefinidamente: deja el navegador abierto hasta cierre manual; la traza se guarda antes de esperar.
   - Resultados y evidencias:
     - `data/last_cart_results.json` (detalle por URL)
     - `data/screens/` (capturas y HTML en caso de fallo)
     - `data/trace.zip` (traza Playwright)

Variables útiles en `.env` (ya definidas en `.env.example`): `MRC_POSTAL_CODE`, `MRC_AUTOMATION_HEADLESS`, `MRC_AUTOMATION_KEEP_OPEN_SECONDS`, `MRC_AUTOMATION_SLOW_MO_MS`, `MRC_AUTOMATION_STORAGE`.

## CI/CD
- Ver prácticas y estrategia en `docs/CI-CD.md`.
- Workflows activos: `/.github/workflows/ci.yml` (tests en PR y pushes a master).

## Seguridad y cumplimiento
- Variables sensibles en `.env` (nunca commitear).
- Respeto de TOS/rate limits; acciones críticas requieren confirmación explícita.

---

Consulta el progreso y detalles de cada iteración en `ITERATIONS.md`.
