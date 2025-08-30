# Diario de iteraciones

Este documento registra objetivos, decisiones, cambios, pruebas y aprendizajes de cada iteración.

## Plantilla
- __Objetivo__:
- __Alcance__:
- __Criterios de aceptación__:
- __Diseño UX/UI__:
- __Implementación__:
- __Pruebas__:
- __Riesgos y mitigaciones__:
- __Métricas/Resultados__:
- __Aprendizajes y próximos pasos__:

---

## I0 – Setup & Descubrimiento
- __Objetivo__: Acordar stack, interfaz, idioma, alcance y plan de pruebas. Investigar API de Mercadona.
- __Alcance__:
  - Decisiones iniciales (stack, interfaz, idioma, tienda/país, persistencia).
  - Borrador de arquitectura y seguridad.
  - Plan de métricas de éxito.
- __Criterios de aceptación__:
  - README actualizado con roadmap y decisiones abiertas.
  - ITERATIONS.md creado.
  - Lista de preguntas pendientes respondidas.
- __Diseño UX/UI__: N/A (definición de principios y flujo mínimo para I1).
- __Implementación__:
  - Se creó `README.md` con propuesta de valor, roadmap y buenas prácticas.
  - Se creó `ITERATIONS.md` (este documento).
- __Pruebas__: N/A.
- __Riesgos y mitigaciones__:
  - API Mercadona puede cambiar o requerir auth propietaria → diseñar cliente con mocks y fallback manual.
  - Límites de uso/TOS → respetar rate limits y confirmar acciones críticas.
- __Métricas/Resultados__: Por definir (tiempo de creación de lista, % cobertura de mapeo a productos, NPS del flujo).
- __Aprendizajes y próximos pasos__:
  - Esperando decisiones de stack e interfaz para arrancar I1.

---

## I1 – Generador de lista (sin API)
- __Objetivo__: Permitir crear y validar una lista de la compra a partir de entradas simples.
- __Alcance__: Normalización, categorías, unidades, UI mínima y tests unitarios.
- __Estado__: Pendiente.

## I2 – Búsqueda de productos (read-only)
- __Objetivo__: Mapear ítems a productos reales con alternativas.
- __Estado__: Pendiente.

## I3 – Preparación de carrito (pre-checkout)
- __Objetivo__: Añadir productos seleccionados al carrito con confirmación previa a compra.
- __Alcance__:
  - Integración Playwright básica.
  - Manejo de cookies y CP en home.
  - Persistencia de sesión (`storage_state`) y endpoint/UI de “Configurar sesión”.
- __Criterios de aceptación__:
  - Se puede abrir la home, aceptar cookies y fijar CP.
  - El estado (CP/login) persiste para ejecuciones posteriores.
  - Endpoint `POST /cart/setup-session` y botón en `index.html` funcionan.
- __Implementación__:
  - `src/mercadona_agent/application/cart_automation.py`: `setup_session()` y flujo inicial de `add_by_urls()`.
  - `src/mercadona_agent/ui_web/app.py`: endpoint `/cart/setup-session`.
  - `src/mercadona_agent/ui_web/templates/index.html`: botón “Configurar sesión (CP/Login)”.
  - `.env.example`: variables `MRC_POSTAL_CODE`, `MRC_AUTOMATION_*`.
- __Pruebas__:
  - Manual: configurar sesión con CP y verificar que no reaparece el modal.
- __Riesgos y mitigaciones__:
  - Variantes de modal CP → múltiples selectores y persistencia de estado.
- __Estado__: Completado.

## I4 – Carrito robusto (una pestaña, sin login)
- __Fecha__: 2025-08-30
- __Objetivo__: Hacer el flujo fiable sin login: una `page` para N URLs, verificación post-click, reintentos y capturas.
- __Alcance__:
  - Manejo robusto de cookies y CP/tienda en cualquier página.
  - Detección fiable del botón “Añadir”.
  - Verificación tras click (toast/badge/mini-carrito) y reintentos.
  - Evidencias de error (screenshots) y persistencia del `storage_state`.
- __Implementación__:
  - `cart_automation.py`:
    - Helpers: `_accept_cookies`, `_handle_cp_modal`, `_find_add_button`, `_verify_added`, `_screenshot`.
    - `add_by_urls()`: `wait_until="networkidle"`, 3 reintentos, verificación y screenshot en fallo.
  - `pyproject.toml`: añadida dependencia `playwright>=1.46`.
- __Pruebas__:
  - Manual: pegar 2–3 URLs y ejecutar “Añadir al carro (auto)”; revisar que se añaden o que se generan capturas en `data/screens/` en caso de fallo.
- __Riesgos y mitigaciones__:
  - Cambios UI (nombres de toasts/badge) → regex y múltiples selectores.
  - Productos con variantes → pendiente ampliar `solve_variants`.
- __Métricas/Resultados__:
  - Mínimo: feedback por URL (OK/ERROR) agregado en UI.
- __Aprendizajes y próximos pasos__:
  - Añadir breakdown por URL en UI.
  - Exponer overrides de `slow_mo`/`keep_open` en formulario.
  - Detectar request de red de “add-to-cart” como verificación adicional.
  - Tests e2e con Playwright.

## I5 – API-first y limpieza de carrito
- __Fecha__: 2025-08-30
- __Objetivo__: Acelerar y robustecer el añadido al carrito permitiendo:
  - Intento por API interna (API-first) usando la misma sesión del navegador.
  - Opción de vaciar el carrito antes de procesar URLs.
- __Alcance__:
  - `cart_automation.py`:
    - `add_by_urls(urls, api_first=False, clear_cart=False)` añade flags y flujo:
      - `api_first`: si hay `product_id`, intenta `POST /api/carts...` clonando una muestra de red capturada.
      - `clear_cart`: visita `/cart` e intenta “Vaciar” o eliminar líneas.
    - Captura de respuestas de red relacionadas con `cart|bag` y guardado en `data/cart_api_samples.json`.
    - Persistencia de resultados detallados en `data/last_cart_results.json` y traza en `data/trace.zip`.
  - UI Web:
    - Endpoint `POST /cart/add-by-urls` acepta `api_first` y `clear_cart`.
    - `index.html` añade checkboxes “API-first” y “Vaciar carrito antes”.
- __Criterios de aceptación__:
  - Con “API-first” activado y `product_id` válido, algunas URLs se añaden sin pulsar botón si la API responde 2xx.
  - Con “Vaciar carrito antes”, el carrito queda vacío antes de iniciar el ciclo de añadido.
  - Se generan artefactos: `data/last_cart_results.json`, `data/cart_api_samples.json`, `data/screens/*`, `data/trace.zip`.
- __Pruebas__:
  - Manual: ejecutar “Añadir al carro (auto)” con ambos toggles en distintas combinaciones; revisar contadores/toasts y artefactos.
- __Riesgos y mitigaciones__:
  - Cambios en endpoints internos → el motor usa muestras capturadas dinámicamente y reintenta por UI si falla.
  - Sesión/CSRF inválidos → usar “Configurar sesión (CP/Login)” y estado persistente (`storage_state`).
- __Métricas/Resultados__:
  - Aumento de tasa de éxito y/o menor tiempo por URL donde la API-first aplica.
- __Aprendizajes y próximos pasos__:
  - Añadir opción “vaciar carrito por API” cuando se conozca el endpoint estable.
  - Mostrar en UI el desglose por URL (origen: UI vs API) y tiempo por operación.
