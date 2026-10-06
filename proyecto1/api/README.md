# api/ — API de inferencia (FastAPI)

Servicio `inference-api` del [`docker-compose.yaml`](../docker-compose.yaml), expuesto en el **puerto 8000**. Carga el modelo más reciente publicado por el DAG en MinIO y responde predicciones del tipo de cobertura forestal (`Cover_Type`).

Documentación interactiva (Swagger): **http://localhost:8000/docs**

## Endpoints

| Método | Ruta | Descripción | Respuestas |
|---|---|---|---|
| `GET` | `/health` | Estado del servicio y nombre del modelo cargado (`null` si no hay ninguno). | 200 |
| `GET` | `/models` | Metadatos de todos los modelos disponibles en MinIO (accuracy, F1 macro, fecha…) y cuál está cargado. | 200 |
| `POST` | `/reload` | Fuerza la recarga del modelo más reciente. | 200, 404 si no hay modelos |
| `POST` | `/predict` | Predice `Cover_Type` para una observación. | 200, 422 si la entrada es inválida, 503 si no hay modelo o no se alcanza MinIO |

### Ejemplo de predicción

```bash
curl -s -X POST localhost:8000/predict -H "Content-Type: application/json" -d '{
  "Elevation": 3142, "Aspect": 59, "Slope": 14,
  "Horizontal_Distance_To_Hydrology": 421, "Vertical_Distance_To_Hydrology": 61,
  "Horizontal_Distance_To_Roadways": 1471,
  "Hillshade_9am": 230, "Hillshade_Noon": 210, "Hillshade_3pm": 110,
  "Horizontal_Distance_To_Fire_Points": 3415,
  "Wilderness_Area": "Commanche", "Soil_Type": "C7757"}'
```

Forma de la respuesta:

```json
{
  "prediction": 0,
  "model_name": "covertype_rf_20260927T185421",
  "model_accuracy": 0.9632,
  "model_created_at": "2026-09-27T18:54:21"
}
```

El ejemplo de entrada es una fila real que devolvió la API del profesor, y viene precargado en Swagger. `prediction` es un entero entre 0 y 6.

## Estructura

| Archivo | Responsabilidad |
|---|---|
| `app/main.py` | Endpoints y `lifespan`: al arrancar intenta cargar un modelo, pero **nunca** impide que la API arranque. |
| `app/model_registry.py` | `ModelRegistry`: lista modelos en MinIO, elige el más reciente, lo descarga y lo mantiene en memoria. Adaptado del patrón del taller 2, que leía modelos de una carpeta local, a MinIO. |
| `app/schemas.py` | Contrato de entrada (`CoverTypeFeatures`) y salida (`PredictResponse`) con Pydantic. |
| `pyproject.toml` | Dependencias, con las librerías de ML fijadas con `==`. |
| `Dockerfile` | `python:3.10-slim` y `uv`. |

## Cómo se elige y se carga el modelo

1. **Solo cuentan los modelos con `.json`.** El DAG sube el `.json` al final, así que su existencia garantiza que el artefacto está completo.
2. **El más reciente se decide por el nombre**, `covertype_rf_AAAAMMDDTHHMMSS`, que ordenado alfabéticamente queda en orden cronológico. No se usa la fecha de modificación de MinIO, que cambiaría si el objeto se copiara.
3. **En cada `/predict`** se consulta el nombre del último modelo, que es un listado rápido. Solo si cambió se descarga el nuevo. Así, un modelo recién publicado por el DAG se usa en la siguiente petición, sin reiniciar la API.
4. **La carga** lee `metadata["model_file"]` y hace `joblib.load(io.BytesIO(...))`. `joblib.load` detecta el gzip por sus primeros bytes y lee sin problema un pickle estándar, así que funciona con `.pkl.gz` sin código adicional.
5. **Un `threading.Lock` protege la recarga.** Los endpoints con `def` (no `async def`) corren en varios hilos a la vez, y sin el candado dos peticiones simultáneas podrían descargar el modelo dos veces o leer uno a medio asignar.

**Por qué el más reciente y no el de mejor accuracy** (como en el taller 2): cada modelo se evalúa sobre un conjunto de prueba distinto, así que sus accuracy no son comparables. Además, como el DAG entrena con los datos acumulados, el más reciente es el que vio más datos.

**Las columnas se ordenan según `metadata["features"]`**, que guardó el DAG. La lista de columnas viaja con el modelo en vez de estar copiada en el código de la API.

## Validación de la entrada

`CoverTypeFeatures` declara cada campo con nombre y tipo. Se descartó recibir una lista de números sin nombres, como en el taller 2: con 12 valores, dos de ellos texto, un error de orden daría predicciones erróneas sin ningún aviso. Los `Hillshade_*` se validan en el rango 0–255 que indica el enunciado. Si un valor está fuera de rango o falta un campo, FastAPI responde **422** antes de llegar al modelo.

Una categoría desconocida en `Wilderness_Area` o `Soil_Type` **no** produce error: el `OneHotEncoder(handle_unknown="ignore")` del modelo la trata como "ninguna categoría conocida".

## Por qué Python 3.10 y versiones exactas

El modelo se entrena en Airflow con **scikit-learn 1.0.2, numpy 1.21.6, scipy 1.7.3, pandas 1.3.5 y joblib 1.3.2**. Un pickle de scikit-learn solo es confiable con las mismas versiones, así que la API las fija con `==`.

Python 3.11 queda descartado porque numpy 1.21.6 no existe para esa versión. Python 3.7 serviría, pero ya no tiene soporte y FastAPI dejó de ser compatible con él. **Python 3.10** es la versión en que las cinco librerías tienen *wheels* para ARM y x86 y FastAPI moderno funciona. Para cargar el pickle importa la versión de las librerías, no la de Python: Python 3.10 lee sin problema el protocolo 4 que genera Python 3.7.

> Si se actualiza Airflow, o su archivo de constraints, en `../airflow/`, estas versiones deben actualizarse aquí también.

## Otros detalles

**`ENV PYTHONUNBUFFERED=1` en el Dockerfile.** Sin esto, Python guarda en un buffer los `print` cuando no escribe en una terminal. El mensaje de error del arranque, por ejemplo "No se pudo cargar un modelo al iniciar: …", no aparecía en `docker compose logs`.

**Sin modelo, la API arranca igual.** El `lifespan` atrapa cualquier error de carga y lo imprime; `/predict` responde 503 hasta que exista un modelo.

## Comandos útiles

```bash
docker compose up -d --build inference-api      # reconstruir solo la API
docker compose logs --tail 20 inference-api     # ver el modelo cargado al arrancar
curl -s localhost:8000/health
curl -s -X POST localhost:8000/reload           # si falla, el traceback queda en los logs
```

## Limitaciones

- Sin autenticación. `joblib.load` deserializa pickle, que puede ejecutar código arbitrario: la API confía en el contenido del bucket, al que solo escribe el DAG.
- Usa las credenciales raíz de MinIO. Lo adecuado sería un usuario de solo lectura sobre el bucket `models`.
- Consulta MinIO en cada predicción. Con mucho tráfico convendría un caché con tiempo de vida.
- Existe `uv.lock`, pero el Dockerfile copia solo `pyproject.toml`. Copiar el lock y usar `uv sync --frozen` haría el build completamente reproducible.
