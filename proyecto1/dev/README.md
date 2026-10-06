# dev/ — Entorno local de desarrollo

**No se despliega.** Sirve para escribir y probar el DAG de [`../dags/`](../dags/) en la máquina de desarrollo sin levantar todo el stack, y para correr experimentos. El contenedor real de Airflow sigue siendo la **fuente de verdad**: este entorno no es idéntico a él (ver más abajo).

## Contenido

| Archivo | Para qué |
|---|---|
| `pyproject.toml` / `uv.lock` | Entorno `uv` con `apache-airflow==2.6.0` y las librerías del pipeline, en Python 3.10. |
| `constraints-2.6.0.txt` | Constraints oficiales de Airflow 2.6.0 **para Python 3.10**, la versión de este entorno. |
| `check_dags.sh` | Carga `../dags` con `DagBag`, igual que el scheduler, y muestra errores de importación o los DAGs y tareas encontrados. |
| `experimento_tamano_modelo.py` | Compara tamaño y accuracy de varias configuraciones del modelo con los datos reales. Se ejecuta dentro del contenedor. |

## Primera vez (o si el entorno se rompe)

```bash
cd proyecto1/dev
rm -rf .venv
uv sync
```

## Verificar el DAG antes de desplegar

```bash
./check_dags.sh
```

Resultado esperado:

```
OK: archivos sin errores de importacion. DAGs encontrados: 1
  - pipeline_mlops_grupo7: ['fetch_batch', 'preprocess', 'build_training_set', 'train_model', 'cleanup_models']
```

El script define variables de entorno de mentira: el DAG lee `os.environ[...]` al importarse y solo necesita que existan. No se conecta a Postgres, MinIO ni a la API. También apunta `AIRFLOW_HOME` a `dev/.airflow`, que git ignora, para no ensuciar `~/airflow`.

**Qué detecta y qué no.** Detecta errores de sintaxis, imports que fallan, variables de configuración mal escritas y errores en la definición del DAG. **No** ejecuta las tareas, así que no detecta errores de lógica ni de compatibilidad de versiones. Para eso: `docker compose exec airflow-scheduler airflow tasks test pipeline_mlops_grupo7 <tarea> <fecha>`.

## Experimento de tamaño del modelo

Desde `proyecto1/`:

```bash
docker compose exec -T airflow-scheduler python - < dev/experimento_tamano_modelo.py
```

Se ejecuta **dentro del contenedor**, para usar las versiones reales de scikit-learn y pandas y los datos reales de `train_ready`. El archivo se pasa por la entrada estándar (`-T` y `python -`), así que no hace falta copiarlo dentro del contenedor. Imprime la distribución de clases, el accuracy de referencia (predecir siempre la clase mayoritaria) y una tabla con accuracy, MB, MB comprimido y segundos de entrenamiento por configuración. Con este experimento se eligieron `n_estimators=50` y `max_depth=20` (ver el [README general](../README.md#56-el-modelo-random-forest-reducido-elegido-con-un-experimento)).

## Por qué Python 3.10 y no 3.7

El contenedor de Airflow usa Python 3.7, pero Python 3.7 no tiene versión para Mac con procesador Apple Silicon: `uv python install 3.7` falla con `No download found ... macos-aarch64`. Python 3.10 está dentro del rango que soporta Airflow 2.6.0 (3.7 a 3.10), y es el compromiso elegido.

La consecuencia es que algunas versiones difieren del contenedor. Por ejemplo, pandas es 1.5.3 aquí y 1.3.5 allá. Esto ya causó un caso real: `DataFrame.to_sql` con un engine de SQLAlchemy creado con `future=True` funcionaba aquí y fallaba en el contenedor. **Validar siempre en el contenedor antes de dar algo por terminado.**

## Por qué las constraints están dentro de `pyproject.toml`

Al principio se instalaba con `uv add ... -c constraints-2.6.0.txt`. Pero `uv` aplica `-c` **solo en ese comando** y no lo guarda. El siguiente `uv run` volvía a sincronizar sin restricciones y subía, por ejemplo, `pendulum` a 3.x, con lo que Airflow fallaba al importarse (`TypeError: 'module' object is not callable`).

La solución fue declarar las 643 versiones del archivo en `[tool.uv].constraint-dependencies`. Desde entonces `uv add`, `uv sync` y `uv run` las respetan siempre, sin flags.

## Reglas para no romper el entorno

- Agregar librerías con `uv add <paquete>`. Si choca con Airflow, `uv` lo dirá al resolver.
- Ejecutar `uv` **solo desde la terminal de la propia máquina**. Si otra máquina o una VM con otro sistema operativo ejecuta `uv run` sobre esta carpeta, `uv` reconstruye `.venv` para esa plataforma y rompe el entorno local.
- `.venv/` y `.airflow/` están en `.gitignore`.
