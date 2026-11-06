# Flujo de commits y pull requests de la Etapa 5

Cada integrante trabaja en su rama, hace **mínimo tres commits** y abre un pull request hacia `main`.
La división es una propuesta: ajústenla a lo que hizo cada quien, porque el historial debe reflejar el trabajo real de cada integrante.

## Orden de integración
1. `feature/etapa-5-modelo` → PR 1 (modelo y carga)
2. `feature/etapa-5-flask` → PR 2 (motor OLAP, rutas y vistas); se crea desde `main` después de fusionar el PR 1
3. `feature/etapa-5-documentacion` → PR 3 (documentación y consultas); se crea después de fusionar el PR 2

## Integrante 1 · rama `feature/etapa-5-modelo`
```bash
git checkout main && git pull
git checkout -b feature/etapa-5-modelo
git add climate-mining-app/data/raw/dim_pais_region.csv climate-mining-app/scripts/multidimensional.py
git commit -m "feat(etapa5): construir dimensiones, tabla de hechos y conocimientos del cubo"
git add climate-mining-app/scripts/cargar_modelo.py climate-mining-app/.gitignore
git commit -m "feat(etapa5): carga reproducible del modelo estrella en SQLite con claves y miembro desconocido"
git add climate-mining-app/scripts/verificar_modelo.py
git commit -m "test(etapa5): verificar integridad del modelo y compararlo con los datos tratados"
git add ssis/sql/04_modelo_estrella.sql
git commit -m "feat(etapa5): script del modelo estrella para SQL Server (esquema dw)"
git push -u origin feature/etapa-5-modelo
```

## Integrante 2 · rama `feature/etapa-5-flask`
```bash
git checkout main && git pull
git checkout -b feature/etapa-5-flask
git add climate-mining-app/scripts/olap.py
git commit -m "feat(etapa5): motor OLAP (drill-down, roll-up, slice, dice, pivot) sobre SQLite"
git add climate-mining-app/app.py climate-mining-app/requirements.txt climate-mining-app/templates/base.html
git commit -m "feat(etapa5): rutas, API /api/etapa5/olap y opcion Analisis multidimensional en el menu"
git add climate-mining-app/templates/etapa5 climate-mining-app/static/css/etapa5.css
git commit -m "feat(etapa5): paginas de la seccion con ficha de fuente, periodo y cobertura"
git add climate-mining-app/static/js/etapa5_vistas.js
git commit -m "feat(etapa5): cuatro vistas interactivas con indicadores, graficas y matrices consultadas al modelo"
git push -u origin feature/etapa-5-flask
```

## Integrante 3 · rama `feature/etapa-5-documentacion`
```bash
git checkout main && git pull
git checkout -b feature/etapa-5-documentacion
git add climate-mining-app/scripts/exportar_documentacion.py docs/etapa5/modelo_estrella.md
git commit -m "docs(etapa5): diagrama y diccionario del modelo multidimensional"
git add docs/etapa5/sql
git commit -m "docs(etapa5): scripts de creacion, consultas de analisis y consultas de validacion"
git add docs/etapa5/README.md docs/etapa5/cambios_flask.md docs/etapa5/commits_y_pull_requests.md climate-mining-app/README.md
git commit -m "docs(etapa5): instrucciones de configuracion, carga y ejecucion, y cambios en Flask"
git add .github/pull_request_template.md
git commit -m "chore: plantilla de pull request"
git push -u origin feature/etapa-5-documentacion
```

## Pull requests
Abrir cada PR en GitHub con la plantilla `.github/pull_request_template.md`, pedir revisión de otro integrante y
fusionar en el orden indicado. Antes de fusionar, ejecutar `python scripts/verificar_modelo.py` y revisar la app en local.

Para comprobar el mínimo de commits de cada integrante:
```bash
git shortlog -sn --since="2026-11-01" main
```
