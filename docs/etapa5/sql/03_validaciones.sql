-- ClimaTec - Etapa 5: consultas de verificacion del modelo (SQLite).
-- Generado por scripts/exportar_documentacion.py. Resultado esperado indicado en cada una.

-- [Unicidad de claves] dim_tiempo.id_tiempo sin repetidos (esperado: 0)
SELECT COUNT(*) - COUNT(DISTINCT id_tiempo) FROM dim_tiempo;

-- [Unicidad de claves] dim_tiempo: clave natural (anio, mes) unica (esperado: 0)
SELECT COUNT(*) FROM (SELECT anio, mes FROM dim_tiempo GROUP BY anio, mes HAVING COUNT(*) > 1);

-- [Unicidad de claves] dim_geografia.id_geo sin repetidos (esperado: 0)
SELECT COUNT(*) - COUNT(DISTINCT id_geo) FROM dim_geografia;

-- [Unicidad de claves] dim_geografia: clave natural (entidad, nivel_geografico) unica (esperado: 0)
SELECT COUNT(*) FROM (SELECT entidad, nivel_geografico FROM dim_geografia GROUP BY entidad, nivel_geografico HAVING COUNT(*) > 1);

-- [Unicidad de claves] dim_indicador.id_indicador sin repetidos (esperado: 0)
SELECT COUNT(*) - COUNT(DISTINCT id_indicador) FROM dim_indicador;

-- [Unicidad de claves] dim_indicador: clave natural (indicador) unica (esperado: 0)
SELECT COUNT(*) FROM (SELECT indicador FROM dim_indicador GROUP BY indicador HAVING COUNT(*) > 1);

-- [Unicidad de claves] dim_fuente.id_fuente sin repetidos (esperado: 0)
SELECT COUNT(*) - COUNT(DISTINCT id_fuente) FROM dim_fuente;

-- [Unicidad de claves] dim_fuente: clave natural (fuente) unica (esperado: 0)
SELECT COUNT(*) FROM (SELECT fuente FROM dim_fuente GROUP BY fuente HAVING COUNT(*) > 1);

-- [Claves foraneas] Todo hecho encuentra su dim_tiempo (esperado: 0)
SELECT COUNT(*) FROM hechos_observacion h LEFT JOIN dim_tiempo d ON d.id_tiempo = h.id_tiempo WHERE d.id_tiempo IS NULL;

-- [Claves foraneas] Todo hecho encuentra su dim_geografia (esperado: 0)
SELECT COUNT(*) FROM hechos_observacion h LEFT JOIN dim_geografia d ON d.id_geo = h.id_geo WHERE d.id_geo IS NULL;

-- [Claves foraneas] Todo hecho encuentra su dim_indicador (esperado: 0)
SELECT COUNT(*) FROM hechos_observacion h LEFT JOIN dim_indicador d ON d.id_indicador = h.id_indicador WHERE d.id_indicador IS NULL;

-- [Claves foraneas] Todo hecho encuentra su dim_fuente (esperado: 0)
SELECT COUNT(*) FROM hechos_observacion h LEFT JOIN dim_fuente d ON d.id_fuente = h.id_fuente WHERE d.id_fuente IS NULL;

-- [Claves foraneas] Restricciones FOREIGN KEY de SQLite (esperado: 0)
PRAGMA foreign_key_check;

-- [Claves foraneas] Miembros de geografia sin hechos (esperado: 0)
SELECT COUNT(*) FROM (SELECT d.id_geo FROM dim_geografia d LEFT JOIN hechos_observacion h ON h.id_geo = d.id_geo WHERE d.id_geo <> -1 GROUP BY d.id_geo HAVING COUNT(h.id_hecho) = 0);

-- [Duplicados en hechos] Una sola fila por indicador × territorio × fecha × fuente (esperado: 0)
SELECT COUNT(*) FROM (SELECT id_tiempo, id_geo, id_indicador, id_fuente FROM hechos_observacion GROUP BY id_tiempo, id_geo, id_indicador, id_fuente HAVING COUNT(*) > 1);

-- [Duplicados en hechos] Hechos cargados = registros tratados (esperado: 21369)
SELECT COUNT(*) FROM hechos_observacion;

-- [Faltantes y desconocidos] Hechos que apuntan al miembro «Desconocido» (-1) (esperado: 0)
SELECT COUNT(*) FROM hechos_observacion WHERE id_tiempo = -1 OR id_geo = -1 OR id_indicador = -1 OR id_fuente = -1;

-- [Faltantes y desconocidos] Hechos sin valor (esperado: 0)
SELECT COUNT(*) FROM hechos_observacion WHERE valor IS NULL;

-- [Faltantes y desconocidos] Hechos sin valor_z (se dejan en NULL) (esperado: informativo)
SELECT COUNT(*) FROM hechos_observacion WHERE valor_z IS NULL;

-- [Faltantes y desconocidos] Entidades sin codigo ISO → «No aplica» (esperado: informativo)
SELECT COUNT(*) FROM dim_geografia WHERE iso_code = 'No aplica' AND id_geo <> -1;

-- [Faltantes y desconocidos] Paises sin region asignada (esperado: 0)
SELECT COUNT(*) FROM dim_geografia WHERE nivel_geografico = 'Nacional' AND region = 'Sin region';

-- [Faltantes y desconocidos] Periodos anuales con mes = 0 («no aplica») (esperado: informativo)
SELECT COUNT(*) FROM dim_tiempo WHERE mes = 0 AND id_tiempo <> -1;

-- [Jerarquias] Cada pais pertenece a una sola region (esperado: 0)
SELECT COUNT(*) FROM (SELECT pais FROM dim_geografia WHERE nivel_geografico = 'Nacional' GROUP BY pais HAVING COUNT(DISTINCT region) > 1);

-- [Jerarquias] Cada mes pertenece a un solo trimestre y semestre (esperado: 0)
SELECT COUNT(*) FROM (SELECT mes FROM dim_tiempo WHERE mes > 0 GROUP BY mes HAVING COUNT(DISTINCT trimestre) > 1 OR COUNT(DISTINCT semestre) > 1);

-- [Jerarquias] Cada indicador pertenece a una sola categoria (esperado: 0)
SELECT COUNT(*) FROM (SELECT indicador FROM dim_indicador GROUP BY indicador HAVING COUNT(DISTINCT categoria) > 1);

-- [Jerarquias] Cada fuente tiene un solo proveedor y tipo (esperado: 0)
SELECT COUNT(*) FROM (SELECT fuente FROM dim_fuente GROUP BY fuente HAVING COUNT(DISTINCT proveedor) > 1 OR COUNT(DISTINCT fuente_tipo) > 1);

-- =====================================================================
-- Comparaciones con los datos tratados (el mismo resultado se calcula con pandas sobre clima_limpio.csv)
-- =====================================================================

-- Numero de registros por anio · pandas: df.groupby('anio').size()
SELECT t.anio, SUM(h.n_registros) AS n FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo GROUP BY t.anio ORDER BY t.anio;

-- Emisiones de CO2 de 2024 por region (Mt CO2) · pandas: df[paises, CO2, 2024].merge(dim_pais_region).groupby('region')['valor'].sum()
SELECT g.region, SUM(h.valor) FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador WHERE i.indicador = 'Emisiones de CO2 (total)' AND g.nivel_geografico = 'Nacional' AND t.anio = 2024 GROUP BY g.region;

-- Anomalia de temperatura: promedio anual por proveedor (°C) · pandas: df[anomalia].groupby(['proveedor', 'anio'])['valor'].mean()
SELECT f.proveedor, t.anio, AVG(h.valor) FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_fuente f ON f.id_fuente = h.id_fuente JOIN dim_indicador i ON i.id_indicador = h.id_indicador WHERE i.indicador = 'Anomalia de temperatura global' GROUP BY f.proveedor, t.anio ORDER BY 1, 2;

-- Registros atipicos por nivel geografico · pandas: df.groupby('nivel_geografico')['atipico'].agg(['sum', 'size'])
SELECT g.nivel_geografico, SUM(h.atipico), SUM(h.n_registros) FROM hechos_observacion h JOIN dim_geografia g ON g.id_geo = h.id_geo GROUP BY g.nivel_geografico;

-- Control puntual: la unidad Colombia 2024 · pandas: df[(entidad == 'Colombia') & (anio == 2024)]
SELECT i.indicador, h.valor FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador WHERE g.entidad = 'Colombia' AND t.anio = 2024;
