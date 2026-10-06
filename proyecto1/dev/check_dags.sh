#!/usr/bin/env bash
# Verifica que los DAGs de proyecto1 se pueden importar, igual que lo haria Airflow.
# Uso (desde cualquier carpeta):   ./proyecto1/dev/check_dags.sh
#
# - Las variables de entorno son DUMMY: solo tienen que existir, porque el DAG
#   lee os.environ[...] al importarse. No se conecta a Postgres/MinIO/API.
# - AIRFLOW_HOME apunta a una carpeta local ignorada por git para no ensuciar ~/airflow.
set -euo pipefail

DEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAGS_DIR="$(cd "$DEV_DIR/../dags" && pwd)"
cd "$DEV_DIR"

export AIRFLOW_HOME="$DEV_DIR/.airflow"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__CORE__UNIT_TEST_MODE=True
export PYTHONPATH="$DAGS_DIR"
export MLOPS_DB_URI="postgresql+psycopg2://x:x@localhost:5432/x"
export EXTERNAL_API_BASE_URL="http://localhost:9999"
export GRUPO_NUMERO=7
export MINIO_ENDPOINT="localhost:9000"
export MINIO_ROOT_USER=x
export MINIO_ROOT_PASSWORD=x
export MINIO_BUCKET=models

uv run python - "$DAGS_DIR" <<'PY'
import sys
from airflow.models import DagBag

dagbag = DagBag(dag_folder=sys.argv[1], include_examples=False)

if dagbag.import_errors:
    print("ERRORES DE IMPORTACION:")
    for path, err in dagbag.import_errors.items():
        print(f"\n--- {path}\n{err}")
    sys.exit(1)

print(f"OK: archivos sin errores de importacion. DAGs encontrados: {len(dagbag.dags)}")
for dag_id, dag in dagbag.dags.items():
    print(f"  - {dag_id}: {[t.task_id for t in dag.tasks]}")
PY
