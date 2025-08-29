# CI/CD – Prácticas y estrategia

Este documento describe cómo automatizamos calidad, pruebas y releases para MercadonaAgent.

## Objetivos
- **Calidad constante**: evitar regressions con checks automáticos en cada PR.
- **Historia limpia y trazable**: GitGraph claro con squash merge y Conventional Commits.
- **Releases fiables**: versionado semántico y artefactos reproducibles.
- **Seguridad**: gestión de secretos y escáneres opcionales.

## Triggers
- Pull Request hacia `master`: ejecuta pipeline de CI completa.
- Push a `master`: CI + publicación de artefactos (si aplica).
- Tag `v*`: proceso de release (changelog, release notes, empaquetado).

## Pipeline (CI)
1. **Setup**
   - Matriz Python: 3.10, 3.11.
   - Cache de dependencias (pip) por `hashFiles('pyproject.toml')`.
2. **Linter/Format** (opcional si se añade pre-commit)
   - black, isort, flake8/ruff (a decidir en I1/I2).
3. **Tests**
   - `pytest -q` con cobertura.
   - Publicar reporte de cobertura (badge futuro).
4. **Seguridad** (opcional)
   - Dependabot para actualizaciones.
   - CodeQL/Semgrep si procede.

## Pipeline (CD)
- Para este MVP (CLI Python):
  - En tags `v*`: crear GitHub Release con changelog y subir artefactos (wheel/sdist).
  - Publicación a PyPI (opcional, puede ser TestPyPI) usando secrets (`PYPI_API_TOKEN`).
- Futuro (cuando haya UI web):
  - Despliegue a ambiente de preview en PR (Netlify/Vercel) y a `prod` en release.

## Versionado y changelog
- **SemVer**: `MAJOR.MINOR.PATCH`.
- **Tags**: `v0.x.y`.
- **Changelog**: generado desde Conventional Commits en release.

## Gestión de secretos
- Nunca en el repo. Usar GitHub Actions Secrets:
  - `PYPI_API_TOKEN` (si se publica), `MERCADONA_USERNAME`, `MERCADONA_PASSWORD`.
- Local: `.env` (gitignored).

## Checklists en PR
- Tests y linters verdes.
- Título estilo Conventional Commits.
- Plantilla PR completada (contexto, cómo probar, iteración/issue).

## Ejemplo de workflow (referencia)
```yaml
# .github/workflows/ci.yml
name: CI
on:
  pull_request:
    branches: [ master ]
  push:
    branches: [ master ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [ '3.10', '3.11' ]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install -e .[dev]
      - name: Run tests
        run: pytest -q
```

## Ejemplo de release (referencia)
```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: [ 'v*' ]

jobs:
  build-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Build dist
        run: |
          python -m pip install --upgrade pip build twine
          python -m build
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/*.whl
            dist/*.tar.gz
      # Opcional: publicar en (Test)PyPI
      - name: Publish to PyPI
        if: secrets.PYPI_API_TOKEN != ''
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: |
          python -m twine upload dist/*
```

## Métricas de calidad
- % cobertura de tests (objetivo inicial: 70% en I1, subir en I2/I3).
- Tiempo medio de pipeline.
- Ratio de PRs fallidas por calidad.

## Roadmap CI/CD
- I1: CI básica (tests). Añadir linter/format.
- I2: Mocks de API en tests de integración, badge de cobertura.
- I3: Release con tags, artefactos y (opcional) publicación a PyPI.
