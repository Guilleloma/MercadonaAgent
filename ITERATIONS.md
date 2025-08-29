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
- __Estado__: Pendiente.
