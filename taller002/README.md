# Taller 002 — Desarrollo en Contenedores con `uv`

Entorno de desarrollo para Machine Learning con **Docker Compose** y
dos servicios, cada uno con sus dependencias gestionadas por **`uv`**:

- **`jupyter`** (carpeta `ml_jupyter/`): JupyterLab instalado con `uv`,
  usado para entrenar modelos.
- **`fastapi`** (carpeta `ml_api/`): API en FastAPI instalada con `uv`,
  usada para servir inferencias.

Los dos contenedores comparten la carpeta `./models` como **volumen**:
el notebook escribe ahí cada modelo que entrena, y la API lee de ahí
mismo. Cuando el notebook guarda un modelo nuevo, la API lo detecta y
lo consume automáticamente, **sin necesidad de reconstruir ni
reiniciar el contenedor de la API**.

```
taller002/
├── docker-compose.yml
├── ml_jupyter/               # servicio JupyterLab
│   ├── Dockerfile
│   ├── pyproject.toml        # deps instaladas con uv (jupyterlab, sklearn, joblib...)
│   └── train_model.ipynb     # entrena y guarda modelos versionados
├── ml_api/                   # servicio API
│   ├── Dockerfile
│   ├── pyproject.toml        # deps instaladas con uv (fastapi, uvicorn, sklearn, joblib)
│   └── app/
│       ├── main.py
│       ├── carga_modelo.py         # registro dinámico del modelo más reciente
│       ├── modelo_de_datos.py      # esquemas Pydantic (request/response)
│       ├── respuestas_y_estados.py # endpoints /health, /models, /reload, /predict
│       └── metodos.py              # endpoints de ejemplo (no relacionados al ML)
└── models/                   # <- VOLUMEN COMPARTIDO entre jupyter y fastapi
```

## 1. Levantar el entorno

```bash
docker compose up --build
```

- JupyterLab: <http://localhost:8888> (token: `devtoken`, configurable
  con la variable `JUPYTER_TOKEN` en `docker-compose.yml`).
- API: <http://localhost:8000> (docs interactivas en
  <http://localhost:8000/docs>).

## 2. Entrenar un modelo

1. Abre JupyterLab y entra con el token `devtoken`.
2. Abre `train_model.ipynb` y ejecuta todas las celdas. Se entrena un
   `RandomForestClassifier` sobre el dataset *iris* y se guarda en
   `models/` (la misma carpeta `./models` del host, gracias al volumen
   compartido):
   - `model_<timestamp>.joblib` — el modelo serializado.
   - `model_<timestamp>.json` — metadatos (accuracy, features, clases).
3. Vuelve a ejecutar la celda de entrenamiento con otros hiperparámetros
   para generar un **modelo nuevo**. La API siempre usa el más reciente
   por fecha de modificación.

### También hay un notebook de pingüinos

`train_model_penguins.ipynb` entrena un `DecisionTreeClassifier` sobre
el dataset *Palmer Penguins* (paquete `palmerpenguins`, viene con el
CSV incluido, no necesita internet). Guarda el modelo con el mismo
formato (`model_<timestamp>.joblib` + `.json` con `feature_names` y
`target_names`), así que la API lo consume sin ningún cambio de
código: no le importa de qué dataset viene un modelo, solo lee sus
metadatos.

**Ojo:** si entrenas primero con `train_model.ipynb` (iris) y después
con `train_model_penguins.ipynb`, la API pasa a usar automáticamente
el de pingüinos (siempre sirve el `.joblib` más reciente por fecha),
y viceversa. Si le mandas a `/predict` un vector `features` con la
cantidad de columnas que no corresponde al modelo actualmente cargado,
la API responde `422` en vez de una predicción incorrecta silenciosa
(valida `len(features)` contra `feature_names` de los metadatos).

## 3. Consumir el modelo desde la API

```bash
curl http://localhost:8000/health
curl http://localhost:8000/models

curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [5.1, 3.5, 1.4, 0.2]}'
```

(El dataset iris tiene 4 features: sepal length, sepal width, petal
length, petal width, en centímetros.)

Forzar recarga manual (normalmente no hace falta, `/predict` ya
recarga solo si detecta un archivo más nuevo):

```bash
curl -X POST http://localhost:8000/reload
```

## 4. Qué estaba roto y qué se corrigió

Al conectar este proyecto se encontraron varias inconsistencias entre
lo que pedía el enunciado y lo que había armado; esto es lo que se
corrigió, archivo por archivo:

- **`Docker-Compose.yaml` → `docker-compose.yml`**: el nombre con
  mayúsculas no es uno de los que `docker compose` detecta
  automáticamente (los válidos son `compose.yaml`, `compose.yml`,
  `docker-compose.yaml`, `docker-compose.yml`, todo en minúscula), así
  que `docker compose up` no lo habría encontrado sin `-f`. Se
  renombró (con `mv`, sin perder el contenido).
- **`build: ./fastAPI`**: esa carpeta no existe, el servicio se llama
  `ml_api`. El build habría fallado de inmediato. Corregido a
  `context: ./ml_api`.
- **Servicio `jupyter` con `image: jupyter/base-notebook`**: no
  cumplía el requisito de "JupyterLab instalado mediante uv" — era una
  imagen genérica de la comunidad, sin `uv`, sin `scikit-learn`, sin
  `joblib`. Se creó `ml_jupyter/Dockerfile`, que instala `uv` y corre
  `uv sync` sobre `ml_jupyter/pyproject.toml`.
- **No existía ningún `Dockerfile` para `ml_api` ni para `ml_jupyter`**
  (solo había un `Dockerfile` suelto en la raíz, que usaba `pip` +
  `requirements.txt` — un archivo que tampoco existe — y no lo
  referenciaba el compose). Se crearon los dos `Dockerfile` que faltan,
  ambos basados en `uv`.
- **`ml_jupyter/pyproject.toml` no tenía `jupyterlab` ni `scikit-learn`
  ni `joblib`** como dependencias — solo `numpy` y `pandas`. Sin
  `jupyterlab` ni siquiera se podía levantar JupyterLab en ese
  contenedor. Se agregaron las tres.
- **Desajuste total entre el notebook y la API**: el notebook
  (`train_model.ipynb`) entrena sobre el dataset *iris* y guarda con
  `joblib` en archivos versionados `model_<timestamp>.joblib`. Pero
  `ml_api/app/carga_modelo.py` esperaba un archivo fijo llamado
  `decision_tree_penguins.pkl` guardado con `pickle`, con features de
  pingüinos (`bill_length_mm`, `island_Dream`, ...). Nunca iban a
  coincidir — la API jamás habría podido consumir lo que el notebook
  produce. Se reescribió `carga_modelo.py` como un registro dinámico
  que escanea `MODELS_DIR`, toma el `.joblib` más reciente por fecha de
  modificación, y lo recarga automáticamente si aparece uno nuevo (esto
  es justo lo que pide el enunciado: "cuando un nuevo modelo es
  guardado en el notebook, la API puede consumirlo").
- **La API cargaba el modelo una sola vez al importar el módulo**
  (`modelos = cargar_modelos()` a nivel de módulo): aunque el archivo
  hubiera coincidido, un modelo nuevo del notebook solo se habría
  reflejado reiniciando el contenedor de la API. Ahora cada request a
  `/predict` llama a `refresh_if_needed()`, que compara fechas de
  modificación y recarga si hace falta.
- **`modelo_de_datos.py`** tenía una clase `PenguinFeatures` (que no
  aplicaba a iris) y restos sueltos de otro tutorial (`Item`, un
  `app = FastAPI()` sin usar). Se reemplazó por un esquema genérico
  `PredictRequest`/`PredictResponse` que valida la cantidad de features
  contra los metadatos del modelo cargado.
- **`respuestas_y_estados.py`**: el endpoint `/predict/{nombre_modelo}`
  buscaba modelos por nombre fijo (`decision_tree`, `svm`) que nunca
  llegaron a existir con el flujo real. Se reemplazó por `/predict`
  (usa siempre el modelo vigente) y se agregaron `/health` y `/models`
  para poder inspeccionar qué modelo está cargado.
- **`ml_api/app/` no tenía `__init__.py`**: funcionaba igual gracias a
  los namespace packages implícitos de Python, pero se agregó de forma
  explícita por prolijidad.
- **`ml_api/pyproject.toml`**: le faltaba `joblib` (necesario para leer
  los `.joblib` del notebook) y tenía `pandas` sin uso real; se
  actualizó la lista de dependencias.
- **Volúmenes del notebook**: antes no se montaba el notebook como
  volumen (dependía de la imagen genérica de Jupyter, que no tenía
  ningún notebook propio). Ahora `train_model.ipynb` se monta
  directamente en el contenedor, así los cambios que hagas ahí se
  quedan en tu carpeta del proyecto.

### Lo que se dejó igual (no era parte de lo requerido)

- `ml_api/app/metodos.py` (endpoints `/items/...`): es un ejemplo de
  tutorial de FastAPI sin relación con el modelo de ML; no interfiere,
  se dejó tal cual.
- `models/decision_tree_penguins.pkl`: es un modelo suelto de una
  prueba manual anterior. La API ya no lo usa (solo lee archivos
  `.joblib`), pero no se borró por si querías conservarlo. Se puede
  eliminar sin problema.
- Los archivos en la **raíz** del proyecto (`Dockerfile`,
  `pyproject.toml`, `uv.lock`, `.venv/`): declaran un "workspace" de
  `uv` y un paquete `taller002` que ninguno de los dos contenedores usa
  — cada servicio construye su imagen desde su propia carpeta
  (`ml_api/`, `ml_jupyter/`) con su propio `pyproject.toml`. Parecen
  quedar de una configuración inicial (`uv init` en la raíz) que no
  llegó a integrarse con Docker Compose. No los toqué porque no rompen
  nada, pero si quieres avisame y los limpio/elimino para no dejar
  configuración muerta dando vueltas.

## 5. Por qué `uv`

Cada servicio tiene su propio `pyproject.toml`. En el `Dockerfile` se
copia el binario oficial de `uv` y se corre `uv sync`, que resuelve y
bloquea las dependencias (genera `uv.lock` dentro de la imagen), crea
un entorno virtual aislado (`.venv`) y es mucho más rápido que
`pip install` en reconstrucciones repetidas. Los procesos se arrancan
con `uv run` (`uv run jupyter lab ...`, `uv run uvicorn ...`), que
ejecuta el comando dentro de ese entorno sin activarlo manualmente.

## 6. Detener el entorno

```bash
docker compose down
```

Los modelos entrenados quedan en `./models` en tu máquina (no se
borran al bajar los contenedores).
