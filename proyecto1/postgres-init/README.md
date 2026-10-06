# postgres-init/ — Esquemas y tablas de la base de datos del negocio

Esta carpeta se monta en `/docker-entrypoint-initdb.d` del servicio `postgres-data`. La imagen oficial de PostgreSQL ejecuta los archivos `.sql` y `.sh` de esa carpeta **una sola vez**: cuando el volumen de datos se crea por primera vez. Otros archivos, como este README, los ignora y solo lo indica en su log.

> Si se modifica `init-schemas.sql` después del primer arranque, el cambio **no se aplica solo**. Hay que recrear el volumen con `docker compose down -v` (se pierden los datos) o ejecutar el cambio a mano con `psql`.

## Dos bases de datos separadas

El proyecto tiene dos contenedores de PostgreSQL 13:

| Servicio | Base | Contenido |
|---|---|---|
| `postgres-airflow` | `airflow` | Metadatos internos de Airflow: DAGs, ejecuciones, usuarios. La administra Airflow, no el proyecto. |
| `postgres-data` | `mlops_data` | **Datos del negocio**, en tres esquemas. Esta carpeta la inicializa. |

Se separaron para que el ciclo de vida de los datos recolectados no dependa del orquestador: reinstalar o migrar Airflow no debe poner en riesgo los datos. Ninguna de las dos expone puertos al exterior; Airflow las alcanza por la red interna de Compose (`postgres-data:5432`).

## Tres etapas como tres esquemas

El enunciado pide almacenar información "sin procesar, procesada y lista para entrenamiento". Cada etapa es un **esquema** dentro de la misma base. Se descartaron tres bases distintas o tres contenedores: requieren más conexiones y más recursos, y no permiten consultas cruzadas entre etapas.

| Esquema | Tabla | Quién la crea | Quién escribe | Modo |
|---|---|---|---|---|
| `raw` | `batches` | `init-schemas.sql` | `fetch_batch` | una fila por petición (`INSERT`) |
| `processed` | `covertype_clean` | pandas (`to_sql`), en la primera ejecución | `preprocess` | `append` |
| `train_ready` | `covertype_train` | pandas (`to_sql`) | `build_training_set` | `replace` |

### `raw.batches`

```sql
CREATE TABLE IF NOT EXISTS raw.batches (
    id            SERIAL      PRIMARY KEY,
    fetched_at    TIMESTAMP   NOT NULL DEFAULT NOW(),
    group_number  INTEGER     NOT NULL,
    payload       JSONB       NOT NULL
);
```

`payload` guarda la respuesta **completa** de la API externa, sin transformar: `group_number`, `batch_number` y `data`. Permite reprocesar si cambia la limpieza, sin volver a pedir datos, y deja evidencia exacta de qué entregó la API y cuándo.

### `processed.covertype_clean`

Contiene las 13 columnas del dataset, con las 10 cuantitativas y `Cover_Type` ya numéricas y `Wilderness_Area` / `Soil_Type` como texto, más `source_raw_id`, que apunta a `raw.batches.id`. Crece en cada ejecución e incluye filas repetidas, porque la API entrega porciones aleatorias del mismo lote.

### `train_ready.covertype_train`

Contiene las 12 variables de entrada más `Cover_Type`, **sin duplicados**. Se reemplaza completa en cada ejecución, porque es un derivado recalculable desde `processed`.

**Tablas creadas por pandas.** Es cómodo, pero pandas infiere los tipos y conserva las mayúsculas de los nombres de columna. En Postgres esas columnas se deben escribir **entre comillas dobles**: `"Cover_Type"`, no `Cover_Type`. La alternativa más estricta sería declarar estas tablas aquí con tipos explícitos.

## Consultas útiles

```bash
# Capturas crudas: lote y cantidad de filas de cada una
docker compose exec postgres-data psql -U mlops -d mlops_data -c "
SELECT id, fetched_at, payload->>'batch_number' AS batch,
       jsonb_array_length(payload->'data') AS filas
FROM raw.batches ORDER BY id DESC LIMIT 10;"

# Tamaño de cada etapa
docker compose exec postgres-data psql -U mlops -d mlops_data -c "
SELECT (SELECT COUNT(*) FROM raw.batches) AS raw,
       (SELECT COUNT(*) FROM processed.covertype_clean) AS processed,
       (SELECT COUNT(*) FROM train_ready.covertype_train) AS train_ready;"

# Distribución de clases del conjunto de entrenamiento
docker compose exec postgres-data psql -U mlops -d mlops_data -c "
SELECT \"Cover_Type\", COUNT(*) AS n,
       ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (), 1) AS pct
FROM train_ready.covertype_train GROUP BY 1 ORDER BY 1;"

# Listar esquemas y tablas
docker compose exec postgres-data psql -U mlops -d mlops_data -c "\dt raw.*" -c "\dt processed.*" -c "\dt train_ready.*"
```

Usuario, contraseña y nombre de la base vienen de `POSTGRES_DATA_USER`, `POSTGRES_DATA_PASSWORD` y `POSTGRES_DATA_DB` en `../.env`. Desde Airflow la conexión se arma como `MLOPS_DB_URI` en el compose.
