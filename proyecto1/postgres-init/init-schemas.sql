-- Se ejecuta UNA sola vez: cuando el volumen de postgres-data se crea por primera vez
-- (mecanismo /docker-entrypoint-initdb.d de la imagen oficial de Postgres).
-- Si cambias este archivo despues, necesitas `docker compose down -v` para que vuelva a correr.

-- Esquemas para las 3 etapas de datos del pipeline (raw / processed / train_ready).
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS processed;
CREATE SCHEMA IF NOT EXISTS train_ready;

-- raw.batches: copia fiel (sin transformar) de cada respuesta de la API externa.
-- Se guarda el JSON completo en JSONB para poder reprocesar si cambia la limpieza.
-- La usa fetch_batch_grupo7 (INSERT) y preprocess (SELECT del ultimo lote).
CREATE TABLE IF NOT EXISTS raw.batches (
    id            SERIAL      PRIMARY KEY,
    fetched_at    TIMESTAMP   NOT NULL DEFAULT NOW(),
    group_number  INTEGER     NOT NULL,
    payload       JSONB       NOT NULL
);

-- Las tablas de processed y train_ready NO se crean aqui: las crea pandas
-- (DataFrame.to_sql) la primera vez que el DAG escribe en ellas.
