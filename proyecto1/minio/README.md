# MinIO — Almacenamiento de modelos

MinIO no tiene código propio en este proyecto: se configura por completo en el [`docker-compose.yaml`](../docker-compose.yaml), con los servicios `minio` y `minio-init`. Este README documenta cómo se usa y por qué se configuró así.

| | |
|---|---|
| API S3 | `minio:9000` dentro de Docker; `localhost:9000` desde la máquina |
| Consola web | http://localhost:9001 (usuario y contraseña: `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` del `.env`) |
| Bucket | `models` (`MINIO_BUCKET`) |
| Volumen | `minio-data-volume`, que persiste aunque se borre el contenedor |

## Qué hay en el bucket

Cada modelo es un **par de objetos** con el mismo nombre base, que incluye la hora UTC de entrenamiento:

```
covertype_rf_20260927T185421.pkl.gz   ← pipeline de scikit-learn (pickle protocolo 4 + gzip, ~2,3 MB)
covertype_rf_20260927T185421.json     ← metadatos: accuracy, F1 macro, filas, clases, hiperparámetros...
```

Hay tres reglas que comparten el DAG y la API:

- **El `.json` es la señal de "modelo completo".** El DAG lo sube después del `.pkl.gz` y lo borra antes. La API solo considera modelos que tienen `.json`, así que nunca carga uno incompleto.
- **El orden cronológico sale del nombre**, no de la fecha de modificación del objeto.
- **Retención:** la tarea `cleanup_models` del DAG conserva los **12** modelos más recientes y borra el resto.

Quién usa el bucket: el DAG escribe (`train_model`) y borra (`cleanup_models`); la API solo lee. Ambos usan el cliente `minio` de Python.

## `minio-init`

Es un contenedor de una sola ejecución, con la imagen del cliente `mc`. Espera a que `minio` esté `healthy`, crea el bucket con `mc mb --ignore-existing` y termina con código 0. La API depende de que termine bien (`service_completed_successfully`), así que nunca arranca con el bucket inexistente.

## Por qué la imagen es `pgsty/silo` y no `minio/minio`

El **11 de septiembre de 2026**, MinIO eliminó sus imágenes `minio/minio` y `minio/mc` de Docker Hub. Días después hizo privados sus repositorios en `quay.io`. Durante el desarrollo, ambas rutas fallaron: `pull access denied` en Docker Hub y `401 UNAUTHORIZED` en quay.io.

Se evaluaron varias alternativas:

| Alternativa | Por qué no / por qué sí |
|---|---|
| Chainguard (`cgr.dev/chainguard/minio`) | Gratis solo con `:latest`: no permite fijar la versión. |
| SeaweedFS, Garage | Son compatibles con S3, pero no son MinIO, que es lo que pide el enunciado. |
| **`pgsty/silo:RELEASE.2026-09-16T00-00-00Z`** (elegida) | Fork de MinIO mantenido por PGSTY: **el mismo código**, con otro nombre por temas de marca. Mismo protocolo S3, mismas variables `MINIO_*`, mismo comando `server /data`, consola completa. Imágenes `amd64` y `arm64` con etiqueta fija. |

El cambio fue solo la línea `image:` del compose. El DAG y la API no se modificaron.

**Lección:** usar `:latest` significa no controlar qué versión se descarga, ni siquiera si todavía existe. Por eso la imagen se fija con una etiqueta de versión exacta.

## Healthcheck

```yaml
test: ["CMD", "mc", "ready", "local"]
```

Las imágenes recientes de MinIO no traen `curl`, así que el healthcheck clásico con `curl .../minio/health/live` fallaría para siempre. `mc ready local` es el healthcheck recomendado, y la imagen de Silo incluye `mc`.

## Comandos útiles

```bash
# Listar los modelos
docker compose exec minio sh -c 'mc alias set yo http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD >/dev/null && mc ls yo/models'

# Ver los metadatos de un modelo
docker compose exec minio sh -c 'mc alias set yo http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD >/dev/null && mc cat yo/models/<nombre>.json'

# Espacio usado por el bucket
docker compose exec minio sh -c 'mc alias set yo http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD >/dev/null && mc du yo/models'
```

## Limitaciones

- La imagen de Silo es un fork comunitario. Conviene revisar sus actualizaciones de seguridad antes de usarla en producción real.
- El DAG y la API usan las credenciales **raíz**. Lo correcto sería un usuario con permisos solo sobre `models`: escritura para el DAG, lectura para la API.
- Sin TLS (`secure=False`). Es aceptable dentro de la red interna de Docker, pero no si MinIO se expone fuera de la VM.
