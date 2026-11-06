# Etapa 5 · Análisis multidimensional

Entregables de la Etapa 5 de ClimaTec (cambio climático y eventos externos · Global / Regional / Nacional · 2020–2026).

- **Aplicación publicada:** https://climatec-ctrm.onrender.com → menú **Análisis multidimensional**
- **Repositorio:** https://github.com/veels3122/ClimaTec

## Dónde está cada entregable

| Entregable | Archivo |
|---|---|
| Diagrama y diccionario del modelo | [`modelo_estrella.md`](modelo_estrella.md) (diagrama Mermaid, diccionario, medidas, jerarquías, correspondencia de variables) |
| Scripts de creación de tablas y relaciones | [`sql/01_crear_modelo_sqlite.sql`](sql/01_crear_modelo_sqlite.sql) · versión SQL Server: [`ssis/sql/04_modelo_estrella.sql`](../../ssis/sql/04_modelo_estrella.sql) |
| Procedimiento de transformación y carga | [`climate-mining-app/scripts/cargar_modelo.py`](../../climate-mining-app/scripts/cargar_modelo.py) |
| Consultas de los análisis | [`sql/02_consultas_analisis.sql`](sql/02_consultas_analisis.sql) · motor: [`scripts/olap.py`](../../climate-mining-app/scripts/olap.py) |
| Consultas de validación | [`sql/03_validaciones.sql`](sql/03_validaciones.sql) · [`scripts/verificar_modelo.py`](../../climate-mining-app/scripts/verificar_modelo.py) |
| Datos utilizados | `climate-mining-app/data/raw/clima_limpio.csv` (datos tratados) y `data/raw/dim_pais_region.csv` (país → continente). Para regenerarlos: `python scripts/preparar_datos.py` y `python scripts/limpieza.py` |
| Cambios en la aplicación Flask | [`cambios_flask.md`](cambios_flask.md) |
| Dependencias e instrucciones | [`climate-mining-app/README.md`](../../climate-mining-app/README.md#etapa-5--analisis-multidimensional) |
| Flujo de commits y pull requests | [`commits_y_pull_requests.md`](commits_y_pull_requests.md) |

Los archivos `modelo_estrella.md` y `sql/*.sql` se generan desde el código con
`python scripts/exportar_documentacion.py`, así que coinciden con lo que ejecuta la aplicación.

## Ejecutar en local

```bash
cd climate-mining-app
pip install -r requirements.txt
python scripts/cargar_modelo.py          # crea data/dw/climatec_dw.sqlite
python scripts/verificar_modelo.py       # integridad + comparaciones con los datos tratados
python app.py                            # http://localhost:5000/etapa-5/proposito
```
