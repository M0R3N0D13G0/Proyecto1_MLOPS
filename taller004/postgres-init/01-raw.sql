-- Se ejecuta UNA sola vez: cuando el volumen de postgres-data se crea por primera vez
-- (mecanismo /docker-entrypoint-initdb.d de la imagen oficial de Postgres).
-- Si cambias este archivo despues, necesitas `docker compose down -v` para que vuelva a correr.

-- raw:       datos tal cual vienen de la fuente, sin limpiar (como en taller003).
-- processed: datos limpios listos para entrenar. Los escribe el notebook
--            (DataFrame.to_sql), por eso aqui solo se crea el esquema.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS processed;

-- Mismas columnas que el CSV de Palmer Penguins (taller001/data_sources/penguins.csv).
-- Se guardan con sus valores faltantes (NA -> NULL): la limpieza es trabajo del preprocesamiento.
CREATE TABLE IF NOT EXISTS raw.penguins (
    rowid              INTEGER PRIMARY KEY,
    species            TEXT,
    island             TEXT,
    bill_length_mm     DOUBLE PRECISION,
    bill_depth_mm      DOUBLE PRECISION,
    flipper_length_mm  DOUBLE PRECISION,
    body_mass_g        DOUBLE PRECISION,
    sex                TEXT,
    year               INTEGER
);

-- /data es ./data montado en docker-compose.yaml (solo lectura).
COPY raw.penguins
FROM '/data/penguins.csv'
WITH (FORMAT csv, HEADER true, NULL 'NA');
