# airflow/ — Imagen de Airflow del proyecto

Esta carpeta construye la imagen que usan los tres servicios de Airflow del [`docker-compose.yaml`](../docker-compose.yaml): `airflow-init`, `airflow-webserver` y `airflow-scheduler`. Parte de la imagen oficial `apache/airflow:2.6.0` y le agrega las librerías que necesita el pipeline.

El código del pipeline **no** vive aquí: está en [`../dags/`](../dags/) y se monta dentro de los contenedores como volumen. Así, cambiar el DAG no requiere reconstruir la imagen; el scheduler relee el archivo por sí solo en unos 30 segundos.

## Archivos

| Archivo | Contenido |
|---|---|
| `Dockerfile` | `FROM apache/airflow:2.6.0` e instalación de `requirements.txt` respetando las constraints oficiales. |
| `requirements.txt` | Librerías del pipeline: `psycopg2-binary`, `pandas`, `scikit-learn`, `joblib`, `minio>=7.2`, `requests`. |
| `constraints-3.7.txt` | Archivo oficial de constraints de Airflow 2.6.0 para Python 3.7 ([fuente](https://raw.githubusercontent.com/apache/airflow/constraints-2.6.0/constraints-3.7.txt)). |

## Por qué se instala con constraints

Airflow tiene cientos de dependencias y solo está probado con combinaciones concretas de versiones. El proyecto Airflow publica para cada versión y cada versión de Python un archivo que fija todas esas versiones, y la documentación oficial recomienda instalar siempre con él:

```dockerfile
RUN pip install --no-cache-dir --user -r /requirements.txt --constraint /constraints-3.7.txt
```

El archivo corresponde a **Python 3.7** porque esa es la versión de Python que trae la imagen `apache/airflow:2.6.0` (verificado dentro del contenedor: Python 3.7.16).

**Por qué `requirements.txt` no tiene versiones mínimas.** El primer intento pedía `pandas>=2.2`, y el build falló con `ResolutionImpossible`: el constraint fija `pandas==1.3.5`, y además pandas 2.x no existe para Python 3.7. Se evaluaron dos caminos: aislar las librerías de ML en otro contenedor, o aceptar las versiones que fija el constraint. Se eligió lo segundo por simplicidad. Por eso las librerías van sin versión mínima y el constraint decide. `minio>=7.2` sí conserva su mínimo porque no choca con nada.

## Versiones resultantes

Verificadas dentro del contenedor con `python -c "import sklearn; print(sklearn.__version__)"` (y análogos):

| Librería | Versión |
|---|---|
| Python | 3.7.16 |
| scikit-learn | 1.0.2 |
| numpy | 1.21.6 |
| scipy | 1.7.3 |
| pandas | 1.3.5 |
| joblib | 1.3.2 |
| SQLAlchemy | 1.4.x |
| dill | 0.3.1.1 (dependencia interna de Airflow) |

**Estas versiones importan fuera de Airflow.** El modelo que se entrena aquí se carga en la API, y un pickle de scikit-learn solo es confiable con las mismas versiones de scikit-learn y numpy. Por eso [`../api/pyproject.toml`](../api/pyproject.toml) fija exactamente estas versiones. **Si se cambia la versión de Airflow o el constraint, hay que actualizar también la API.**

## Servicios que usan esta imagen

| Servicio | Comando | Notas |
|---|---|---|
| `airflow-init` | `/entrypoint airflow version` con `_AIRFLOW_DB_UPGRADE=true` y `_AIRFLOW_WWW_USER_CREATE=true` | Corre una vez: migra la base de metadatos y crea el usuario administrador. Corre como root solo para ajustar permisos de `logs/`, `dags/` y `plugins/`. |
| `airflow-webserver` | `webserver` | Interfaz en http://localhost:8080. |
| `airflow-scheduler` | `scheduler` | Programa el DAG y, con **LocalExecutor**, también ejecuta las tareas. |

La configuración común está en el ancla YAML `x-airflow-common` del compose: executor, conexión a `postgres-airflow`, `SECRET_KEY` compartida y las variables que usa el DAG (`MLOPS_DB_URI`, `EXTERNAL_API_BASE_URL`, `GRUPO_NUMERO` y `MINIO_*`).

## Comandos útiles

```bash
# Ejecutar UNA tarea aislada, sin dependencias ni registro de estado (ideal para depurar)
docker compose exec airflow-scheduler airflow tasks test pipeline_mlops_grupo7 train_model 2026-09-27

# Errores de importación de DAGs
docker compose exec airflow-scheduler airflow dags list-import-errors

# Versiones reales de las librerías dentro del contenedor
docker compose exec airflow-scheduler python -c "import sklearn, numpy, pandas; print(sklearn.__version__, numpy.__version__, pandas.__version__)"

# Logs del scheduler
docker compose logs --tail 50 airflow-scheduler
```

Los logs de cada tarea también quedan en `../logs/dag_id=pipeline_mlops_grupo7/`, porque esa carpeta está montada.

## Problemas conocidos

**`bash: /root/bin/pip: Permission denied` al hacer `docker compose exec ... pip`.** La imagen pone `/root/bin` al inicio del `PATH`, y el usuario de Airflow (UID 50000) no tiene permiso sobre `/root`. Hay que usar `python -m pip ...`.

**`ERROR: You need to initialize the database` en bucle.** `airflow-init` no migró la base. La versión actual del compose usa `set -e` y `exec /entrypoint`, así que si la inicialización falla el contenedor termina con un código distinto de 0 y el scheduler no arranca. Para ver la causa: `docker compose logs airflow-init`. La historia completa está en el [README general, sección 7](../README.md#7-problemas-encontrados-y-cómo-se-resolvieron).

**La interfaz da 403 al abrir los logs de una tarea.** Webserver y scheduler deben compartir `AIRFLOW__WEBSERVER__SECRET_KEY`. Viene del `.env`.

**`n_jobs=-1` en scikit-learn no tiene efecto.** Con LocalExecutor las tareas corren en procesos hijos, y `joblib` no puede crear procesos propios desde ahí; lo avisa con `Loky-backed parallel loops cannot be called in a multiprocessing`. El DAG usa `n_jobs=1`.
