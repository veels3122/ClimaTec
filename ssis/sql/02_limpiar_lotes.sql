/* ==========================================================================
   ClimaTec - Etapa ETL (SSIS)
   Script 02: borra TODAS las cargas (lotes, staging y destinos) y reinicia
   los contadores en 1. Usar antes de las iteraciones reales o cuando se
   quiera empezar de cero. NO borra tablas ni procedimientos.
   ========================================================================== */
USE ClimaTec_ETL;
GO
DELETE FROM dbo.clima_revision;
DELETE FROM dbo.clima_limpio;
DELETE FROM dbo.stg_clima;
DELETE FROM dbo.etl_lote;
DBCC CHECKIDENT ('dbo.clima_revision', RESEED, 0);
DBCC CHECKIDENT ('dbo.clima_limpio',   RESEED, 0);
DBCC CHECKIDENT ('dbo.stg_clima',      RESEED, 0);
DBCC CHECKIDENT ('dbo.etl_lote',       RESEED, 0);
GO
SELECT 'etl_lote' AS tabla, COUNT(*) AS filas FROM dbo.etl_lote
UNION ALL SELECT 'stg_clima',      COUNT(*) FROM dbo.stg_clima
UNION ALL SELECT 'clima_limpio',   COUNT(*) FROM dbo.clima_limpio
UNION ALL SELECT 'clima_revision', COUNT(*) FROM dbo.clima_revision;
GO
