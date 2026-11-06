-- ClimaTec - Etapa 5: consultas de analisis sobre el modelo estrella (SQLite).
-- Generado por scripts/exportar_documentacion.py. Cada consulta es la que ejecuta la app.

-- =====================================================================
-- 1. Evidencia de los conocimientos multidimensionales (una o dos por conocimiento)
-- =====================================================================

-- Conocimiento 1 (vista 2): Dentro de Sudamerica, Brazil emite 43,5% del CO2 y Colombia es el pais numero 4
-- Paises de Sudamerica
SELECT g.entidad AS fk, g.entidad AS fl, NULL AS ck, NULL AS cl, SUM(h.valor) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND i.indicador = 'Emisiones de CO2 (total)' AND t.anio = 2024 AND g.nivel_geografico = 'Nacional' AND g.region_es = 'Sudamerica' GROUP BY fk ORDER BY fk;

-- Conocimiento 2 (vista 3): Entre 2020 y 2024 Asia lidera el aumento de emisiones y Oceania y Europa las reducen
-- Territorios en el anio base y el final
SELECT g.entidad AS fk, CASE WHEN g.entidad = 'World' THEN 'Mundo' WHEN g.nivel_geografico = 'Regional' THEN g.region_es ELSE g.entidad END AS fl, t.anio AS ck, CAST(t.anio AS TEXT) AS cl, SUM(h.valor) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND i.indicador = 'Emisiones de CO2 (total)' AND g.entidad IN ('Asia', 'North America', 'Europe', 'Africa', 'South America', 'Oceania', 'World', 'Colombia') AND t.anio IN (2020, 2024) GROUP BY fk, ck ORDER BY fk, ck;

-- Conocimiento 3 (vista 1): El calentamiento se ve en el anio, pero el pico solo aparece al bajar al mes
-- Promedio anual por proveedor
SELECT t.anio AS fk, CAST(t.anio AS TEXT) AS fl, f.proveedor AS ck, f.proveedor AS cl, AVG(h.valor) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND i.indicador = 'Anomalia de temperatura global' GROUP BY fk, ck ORDER BY fk, ck;

-- Conocimiento 3 (vista 1): El calentamiento se ve en el anio, pero el pico solo aparece al bajar al mes
-- Meses de 2023 por proveedor
SELECT t.anio * 100 + t.mes AS fk, t.nombre_mes || ' ' || t.anio AS fl, f.proveedor AS ck, f.proveedor AS cl, AVG(h.valor) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND i.indicador = 'Anomalia de temperatura global' AND t.anio = 2023 AND t.mes > 0 GROUP BY fk, ck ORDER BY fk, ck;

-- Conocimiento 4 (vista 4): La marca de atipico depende del nivel geografico, no solo del dato
-- % de atipicos por nivel y categoria
SELECT g.nivel_geografico AS fk, g.nivel_geografico AS fl, i.categoria AS ck, i.categoria AS cl, 100.0 * SUM(h.atipico) / SUM(h.n_registros) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 GROUP BY fk, ck ORDER BY fk, ck;

-- Conocimiento 5 (vista 1): Dentro de cada anio el CO2 sube y baja 5,5 ppm, mas del doble de lo que aumenta de un anio a otro
-- Promedio por mes calendario
SELECT t.mes AS fk, t.nombre_mes AS fl, NULL AS ck, NULL AS cl, AVG(h.valor) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND i.indicador = 'Concentracion de CO2 atmosferico' AND t.anio IN (2020, 2021, 2022, 2023, 2024, 2025) AND t.mes > 0 GROUP BY fk ORDER BY fk;

-- Conocimiento 6 (vista 2): En Sudamerica, Colombia pesa mas en metano que en CO2 y menos que en poblacion
-- Paises × indicador (suma por celda)
SELECT g.entidad AS fk, g.entidad AS fl, i.indicador AS ck, i.indicador AS cl, SUM(h.valor) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND i.indicador IN ('Emisiones de CO2 (total)', 'Emisiones de metano', 'Emisiones de oxido nitroso', 'Poblacion') AND t.anio = 2024 AND g.nivel_geografico = 'Nacional' AND g.region_es = 'Sudamerica' GROUP BY fk, ck ORDER BY fk, ck;

-- Conocimiento 7 (vista 3): Colombia parte con mas renovables que casi todos, pero es el unico territorio que pierde participacion
-- Participacion de renovables
SELECT g.entidad AS fk, CASE WHEN g.entidad = 'World' THEN 'Mundo' WHEN g.nivel_geografico = 'Regional' THEN g.region_es ELSE g.entidad END AS fl, t.anio AS ck, CAST(t.anio AS TEXT) AS cl, AVG(h.valor) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND i.indicador = 'Participacion de renovables en energia' AND g.entidad IN ('Asia', 'North America', 'Europe', 'Africa', 'South America', 'Oceania', 'World', 'Colombia') AND t.anio IN (2020, 2024) GROUP BY fk, ck ORDER BY fk, ck;

-- Conocimiento 8 (vista 4): Entre paises, los atipicos se reparten parejo entre categorias y no aparecen en las fuentes primarias
-- Categoria con slice Nacional
SELECT i.categoria AS fk, i.categoria AS fl, NULL AS ck, NULL AS cl, 100.0 * SUM(h.atipico) / SUM(h.n_registros) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND g.nivel_geografico = 'Nacional' GROUP BY fk ORDER BY fk;

-- Conocimiento 8 (vista 4): Entre paises, los atipicos se reparten parejo entre categorias y no aparecen en las fuentes primarias
-- % de atipicos por tipo de fuente
SELECT f.fuente_tipo AS fk, f.fuente_tipo AS fl, NULL AS ck, NULL AS cl, 100.0 * SUM(h.atipico) / SUM(h.n_registros) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 GROUP BY fk ORDER BY fk;

-- =====================================================================
-- 2. Ejemplos de operaciones OLAP (drill-down, roll-up, slice, dice, pivot)
-- =====================================================================

-- Drill-down · De la region Sudamerica a sus paises · Antes · nivel Region
SELECT g.region_es AS fk, g.region_es AS fl, NULL AS ck, NULL AS cl, SUM(h.valor) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND i.indicador = 'Emisiones de CO2 (total)' AND t.anio = 2024 AND g.nivel_geografico = 'Nacional' GROUP BY fk ORDER BY fk;

-- Drill-down · De la region Sudamerica a sus paises · Despues · paises de Sudamerica
SELECT g.entidad AS fk, g.entidad AS fl, NULL AS ck, NULL AS cl, SUM(h.valor) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND i.indicador = 'Emisiones de CO2 (total)' AND t.anio = 2024 AND g.nivel_geografico = 'Nacional' AND g.region_es = 'Sudamerica' GROUP BY fk ORDER BY fk;

-- Roll-up · De los meses de 2023 al anio 2023 (anomalia de temperatura, NASA) · Antes · nivel Mes
SELECT t.anio * 100 + t.mes AS fk, t.nombre_mes || ' ' || t.anio AS fl, NULL AS ck, NULL AS cl, AVG(h.valor) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND i.indicador = 'Anomalia de temperatura global' AND f.proveedor = 'NASA' AND t.anio = 2023 AND t.mes > 0 GROUP BY fk ORDER BY fk;

-- Roll-up · De los meses de 2023 al anio 2023 (anomalia de temperatura, NASA) · Despues · nivel Anio
SELECT t.anio AS fk, CAST(t.anio AS TEXT) AS fl, NULL AS ck, NULL AS cl, AVG(h.valor) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND i.indicador = 'Anomalia de temperatura global' AND f.proveedor = 'NASA' AND t.anio = 2023 GROUP BY fk ORDER BY fk;

-- Roll-up · De los indicadores de Energia a la categoria Energia (% de atipicos, paises) · Antes · nivel Indicador
SELECT i.indicador AS fk, i.indicador AS fl, NULL AS ck, NULL AS cl, 100.0 * SUM(h.atipico) / SUM(h.n_registros) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND g.nivel_geografico = 'Nacional' AND i.categoria = 'Energia' GROUP BY fk ORDER BY fk;

-- Roll-up · De los indicadores de Energia a la categoria Energia (% de atipicos, paises) · Despues · nivel Categoria
SELECT i.categoria AS fk, i.categoria AS fl, NULL AS ck, NULL AS cl, 100.0 * SUM(h.atipico) / SUM(h.n_registros) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND g.nivel_geografico = 'Nacional' AND i.categoria = 'Energia' GROUP BY fk ORDER BY fk;

-- Slice · Fijar el indicador «Participacion de renovables en energia» · Rebanada Territorio × Anio
SELECT g.entidad AS fk, CASE WHEN g.entidad = 'World' THEN 'Mundo' WHEN g.nivel_geografico = 'Regional' THEN g.region_es ELSE g.entidad END AS fl, t.anio AS ck, CAST(t.anio AS TEXT) AS cl, AVG(h.valor) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND i.indicador = 'Participacion de renovables en energia' AND g.entidad IN ('Africa', 'Asia', 'Europe', 'North America', 'Oceania', 'South America', 'World', 'Colombia') AND t.anio IN (2020, 2024) GROUP BY fk, ck ORDER BY fk, ck;

-- Dice · Subcubo {Sudamerica, Colombia, Mundo} × {2021, 2024} × CO2 per capita · Subcubo
SELECT g.entidad AS fk, CASE WHEN g.entidad = 'World' THEN 'Mundo' WHEN g.nivel_geografico = 'Regional' THEN g.region_es ELSE g.entidad END AS fl, t.anio AS ck, CAST(t.anio AS TEXT) AS cl, AVG(h.valor) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 AND i.indicador = 'Emisiones de CO2 per capita' AND g.entidad IN ('South America', 'Colombia', 'World') AND t.anio IN (2021, 2024) GROUP BY fk, ck ORDER BY fk, ck;

-- Pivot · Rotar Nivel geografico × Tipo de fuente · Filas: nivel · Columnas: tipo de fuente
SELECT g.nivel_geografico AS fk, g.nivel_geografico AS fl, f.fuente_tipo AS ck, f.fuente_tipo AS cl, SUM(h.n_registros) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 GROUP BY fk, ck ORDER BY fk, ck;

-- Pivot · Rotar Nivel geografico × Tipo de fuente · Filas: tipo de fuente · Columnas: nivel
SELECT f.fuente_tipo AS fk, f.fuente_tipo AS fl, g.nivel_geografico AS ck, g.nivel_geografico AS cl, SUM(h.n_registros) AS v, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador JOIN dim_fuente f ON f.id_fuente = h.id_fuente WHERE h.id_tiempo <> -1 GROUP BY fk, ck ORDER BY fk, ck;

-- =====================================================================
-- 3. Plantilla de las consultas de las vistas (/api/etapa5/olap)
-- =====================================================================
-- SELECT <clave filas>, <clave columnas>, <medida>
-- FROM hechos_observacion h
-- JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo
-- JOIN dim_geografia g ON g.id_geo = h.id_geo
-- JOIN dim_indicador i ON i.id_indicador = h.id_indicador
-- JOIN dim_fuente f ON f.id_fuente = h.id_fuente
-- WHERE <slice / dice> GROUP BY <filas>, <columnas>;
-- Medidas: Numero de registros = SUM(h.n_registros); Registros atipicos = SUM(h.atipico); % de atipicos = 100.0 * SUM(h.atipico) / SUM(h.n_registros); Valor z promedio = AVG(h.valor_z); Valor sumado = SUM(h.valor); Valor promedio = AVG(h.valor); Paises con dato = COUNT(DISTINCT CASE WHEN g.nivel_geografico = 'Nacional' THEN g.id_geo END)
