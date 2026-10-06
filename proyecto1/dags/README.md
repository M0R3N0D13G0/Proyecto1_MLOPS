# dags/ — Pipeline `pipeline_mlops_grupo7`

Esta carpeta se monta en `/opt/airflow/dags` dentro de los contenedores de Airflow. El scheduler relee sus archivos `.py` cada ~30 segundos, así que un cambio aquí se aplica sin reconstruir ni reiniciar nada. Airflow ignora los archivos que no son `.py`, como este README.

Todo el pipeline está en [`pipeline_mlops.py`](pipeline_mlops.py).

## Configuración del DAG

```python
with DAG(
    dag_id="pipeline_mlops_grupo7",
    start_date=datetime(2026, 1, 1),
    schedule="*/5 * * * *",
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "grupo7", "retries": 1, "retry_delay": timedelta(minutes=1)},
)
```

| Parámetro | Valor | Por qué |
|---|---|---|
| `schedule` | cada 5 minutos | Coincide con la rotación de lotes de la API externa; los 10 lotes se cubren en unos 50 minutos. |
| `catchup` | `False` | Con `True`, Airflow crearía una ejecución por cada intervalo desde el 1 de enero: miles de peticiones pendientes contra la API. |
| `start_date` | fecha fija | Nunca `datetime.now()`: el archivo se relee constantemente, y una fecha que se mueve impide programar el DAG. |
| `max_active_runs` | `1` | Si una ejecución tarda más de 5 minutos, la siguiente espera. Nunca hay dos peticiones simultáneas a la API ni dos escrituras concurrentes sobre `train_ready`. |
| `retries` | 1 (0 en `fetch_batch`) | Un reintento absorbe fallos pasajeros de Postgres o MinIO. En `fetch_batch` es 0 porque el enunciado prohíbe hacer más de una petición a la API por ejecución. |

Airflow nombra cada ejecución con el **inicio** de su intervalo, pero la ejecuta al **final**. Por ejemplo, la ejecución `scheduled__...T21:05:00` corre a las 21:10.

## Tareas

```
fetch_batch → preprocess → build_training_set → train_model → cleanup_models
```

Todas son `PythonOperator`. Una tarea solo corre si la anterior terminó bien. Si una falla, las siguientes quedan como `upstream_failed`, no se publica ningún modelo nuevo y la API sigue sirviendo el último modelo válido.

| Tarea | Lee de | Escribe en | Qué hace |
|---|---|---|---|
| `fetch_batch` | API externa `GET /data?group_number=7` | `raw.batches` | Guarda la respuesta **completa** como JSONB, sin transformar. `raise_for_status()` convierte cualquier error HTTP en un fallo visible de la tarea. `timeout=30`. |
| `preprocess` | último registro de `raw.batches` | `processed.covertype_clean` (`append`) | Arma el DataFrame con las 13 columnas, castea a número las 10 cuantitativas y `Cover_Type` (la API manda todo como texto), descarta filas no convertibles y agrega `source_raw_id` para trazabilidad. |
| `build_training_set` | todo `processed.covertype_clean` | `train_ready.covertype_train` (`replace`) | Toma las 12 variables de entrada y el objetivo (deja fuera `source_raw_id`), elimina duplicados y reemplaza la tabla. |
| `train_model` | `train_ready.covertype_train` | MinIO: `<nombre>.pkl.gz` y `<nombre>.json` | Entrena, evalúa, valida el artefacto y lo publica. Detalle abajo. |
| `cleanup_models` | MinIO | MinIO | Conserva los últimos `MODELS_TO_KEEP` modelos y borra el resto. |

## Contrato de datos

La API externa devuelve cada fila como una lista de **13 textos**, en este orden:

| # | Columna | Tipo tras `preprocess` |
|---|---|---|
| 1–10 | `Elevation`, `Aspect`, `Slope`, `Horizontal_Distance_To_Hydrology`, `Vertical_Distance_To_Hydrology`, `Horizontal_Distance_To_Roadways`, `Hillshade_9am`, `Hillshade_Noon`, `Hillshade_3pm`, `Horizontal_Distance_To_Fire_Points` | numérico |
| 11 | `Wilderness_Area` (por ejemplo `"Rawah"`, `"Commanche"`) | texto (categórica) |
| 12 | `Soil_Type` (por ejemplo `"C7757"`) | texto (categórica) |
| 13 | `Cover_Type` (0 a 6) | numérico (objetivo) |

El enunciado describe `Wilderness_Area` y `Soil_Type` como 4 y 40 columnas binarias, pero la API entrega la versión "cruda": una columna de texto cada una. Las columnas están definidas como constantes al inicio del archivo (`COVERTYPE_NUMERIC_COLUMNS`, `COVERTYPE_ALL_COLUMNS`, `FEATURE_COLUMNS`, `TARGET_COLUMN`), para que haya una sola definición.

## `train_model` en detalle

1. **Chequeo de datos mínimos.** Con menos de `MIN_TRAIN_ROWS = 5000` filas únicas o menos de 2 clases, lanza `AirflowSkipException`: la tarea queda *skipped* (rosado), no *failed*, y `cleanup_models` también se salta. Faltar datos es un estado esperado, no un error.
2. **Split** 80/20 con `random_state=42`.
3. **Pipeline:** `ColumnTransformer` con `OneHotEncoder(handle_unknown="ignore")` sobre `Wilderness_Area` y `Soil_Type`, y el resto de columnas sin transformar (`passthrough`); después `RandomForestClassifier(n_estimators=50, max_depth=20, n_jobs=1)`. El encoder va **dentro** del modelo para que la API reciba valores crudos y no tenga que replicar ninguna transformación.
4. **Métricas:** accuracy y F1 macro. El F1 macro es necesario porque las clases 0 y 1 son el 92% de los datos.
5. **Serialización:** `pickle.dumps(model, protocol=4)`. **No se usa `joblib.dump`**: dentro de Airflow, `dill` está importado y `joblib.dump` deja referencias a `dill` que la API no puede resolver. La explicación completa está en el [README general](../README.md#7-problemas-encontrados-y-cómo-se-resolvieron).
6. **Validación:** si el pickle (sin comprimir) contiene `b"dill"`, la tarea falla y no se publica nada.
7. **Compresión:** `gzip.compress(...)`. El artefacto baja de ~16,7 MB a ~2,3 MB.
8. **Publicación:** primero el `.pkl.gz`, **al final** el `.json`. La API solo considera modelos que tienen su `.json`, así que nunca ve uno a medio subir.

Ejemplo de metadatos (`.json`, valores ilustrativos):

```json
{
  "model_name": "covertype_rf_20260927T185421",
  "model_file": "covertype_rf_20260927T185421.pkl.gz",
  "created_at": "2026-09-27T18:54:21",
  "accuracy": 0.9632,
  "f1_macro": 0.9095,
  "n_train_rows": 30351,
  "n_test_rows": 7588,
  "features": ["Elevation", "...", "Wilderness_Area", "Soil_Type"],
  "classes": [0, 1, 2, 4, 5, 6],
  "model_params": {"n_estimators": 50, "max_depth": 20},
  "serialization": "pickle protocol 4 + gzip",
  "size_bytes": 2400000,
  "sklearn_version": "1.0.2"
}
```

La API usa `features` para ordenar las columnas de la petición. Así el orden de columnas viaja con el modelo y no se duplica en el código de la API.

## `cleanup_models`

Ordena los modelos por nombre (que lleva la hora UTC, así que el orden es cronológico) y borra todos menos los `MODELS_TO_KEEP = 12` más recientes. Para cada modelo borra **primero el `.json`** y después el resto de objetos con ese prefijo. Borra por cantidad y no por antigüedad: aunque el DAG deje de entrenar durante días, nunca deja el bucket vacío.

## Constantes ajustables

| Constante | Valor | Cómo se eligió |
|---|---|---|
| `MIN_TRAIN_ROWS` | 5000 | Aproximadamente un lote completo (cada lote trae 5.810 filas). Se supera desde la primera ejecución. |
| `MODEL_N_ESTIMATORS`, `MODEL_MAX_DEPTH` | 50, 20 | Experimento con datos reales ([`../dev/experimento_tamano_modelo.py`](../dev/experimento_tamano_modelo.py)): −0,16 puntos de accuracy y un 60% menos de tamaño. |
| `MODELS_TO_KEEP` | 12 | Una hora de historial, un ciclo completo de los 10 lotes; unos 28 MB en MinIO. |

## Cómo probar cambios

```bash
# Localmente (sin Docker): ¿el DAG importa sin errores?
./dev/check_dags.sh

# En el contenedor: ejecutar una sola tarea sobre los datos reales
docker compose exec airflow-scheduler airflow tasks test pipeline_mlops_grupo7 train_model 2026-09-27
docker compose exec airflow-scheduler airflow tasks test pipeline_mlops_grupo7 cleanup_models 2026-09-27
```

`airflow tasks test` no respeta dependencias ni guarda el estado en la base de Airflow: sirve para probar una tarea sin correr todo el DAG. Con `train_model` y `cleanup_models` no toca la API externa.

## Detalles de implementación

- **Variables de entorno con `os.environ["..."]`**, sin valor por defecto: si falta alguna, el DAG falla al importarse con un error claro.
- **El engine de SQLAlchemy se crea sin `future=True`.** pandas 1.3.5, la versión del contenedor, falla en `to_sql` con el modo "estilo 2.0" de SQLAlchemy 1.4.
- **`pd.read_sql` recibe `text("...")`**, no un string plano, para que funcione con las dos versiones de pandas (contenedor y entorno local).
- **Los imports de scikit-learn van dentro de `train_model`.** El scheduler relee el archivo cada ~30 segundos, y todo lo que está a nivel de módulo se ejecuta en cada lectura. scikit-learn es pesado y solo lo usa esta tarea.
