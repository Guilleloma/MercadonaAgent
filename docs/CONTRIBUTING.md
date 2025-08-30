# Contribuir a MercadonaAgent

## Estrategia de ramas
- Rama protegida: `master` (revisión obligatoria, checks verdes, squash merge).
- Crea ramas cortas desde `master` siguiendo el naming:
  - `feat/<scope>-<breve-descripcion>`
  - `fix/<issue-id|-descripcion>`
  - `docs/…`, `chore/…`, `refactor/…`, `test/…`, `perf/…`
- Relaciona tu rama con una iteración (`I1`, `I2`, `I3`) y, si aplica, con un issue.

## Flujo de trabajo (GitHub Flow)
1. `git checkout -b feature/core-normalizador` desde `master`.
2. Commits pequeños y atómicos siguiendo Conventional Commits.
3. Abre un Pull Request hacia `master` lo antes posible (draft si no está listo).
4. Asegura CI verde (tests/linters) y solicita revisión.
5. Integra con squash merge para mantener historia lineal.

## Convenciones de commits (Conventional Commits)
- Tipos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
- Formato: `tipo(scope): descripcion breve en imperativo`
- Ejemplos:
  - `feat(core): normaliza unidades en generador de lista`
  - `fix(api): reintentos exponenciales en 429`

## Checklist de PR
- [ ] Título siguiendo Conventional Commits
- [ ] Descripción clara (contexto, cambios, decisiones)
- [ ] Enlaza issue/iteración (p. ej. I1)
- [ ] Tests añadidos/actualizados y pasando
- [ ] Cambios visibles documentados en README/ITERATIONS si aplica
- [ ] Sin secretos en código (usa `.env`)

## Calidad y CI
- Ejecuta tests localmente antes del PR.
- Lint/format: se definirá según el stack (Python/Node) en I0/I1.

## Versionado
- Tags semánticos `v0.x.y` al cerrar iteraciones relevantes.

## Seguridad y cumplimiento
- No subas credenciales. Usa variables de entorno y `.env` (gitignored).
- Respeta TOS/robots de la API de Mercadona. Acciones críticas requieren confirmación explícita.
