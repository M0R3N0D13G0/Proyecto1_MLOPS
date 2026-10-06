"""Experimento: tamano del modelo vs accuracy, con los datos REALES de train_ready.

NO es parte del pipeline. Se ejecuta a mano dentro del contenedor de Airflow
(mismas versiones de sklearn/pandas que en produccion), desde proyecto1/:

    docker compose exec -T airflow-scheduler python - < dev/experimento_tamano_modelo.py

Usa el mismo split que train_model (test_size=0.2, random_state=42) para que los
accuracy sean comparables entre configuraciones.
"""
import io
import os
import pickle
import time
import zlib

import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

NUMERIC = [
    "Elevation", "Aspect", "Slope", "Horizontal_Distance_To_Hydrology",
    "Vertical_Distance_To_Hydrology", "Horizontal_Distance_To_Roadways",
    "Hillshade_9am", "Hillshade_Noon", "Hillshade_3pm", "Horizontal_Distance_To_Fire_Points",
]
FEATURES = NUMERIC + ["Wilderness_Area", "Soil_Type"]
TARGET = "Cover_Type"

engine = create_engine(os.environ["MLOPS_DB_URI"])
with engine.connect() as conn:
    df = pd.read_sql(text("SELECT * FROM train_ready.covertype_train"), conn)

X, y = df[FEATURES], df[TARGET].astype(int)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"Filas: {len(df)}  (train={len(X_train)}, test={len(X_test)})")
dist = y.value_counts(normalize=True).sort_index().mul(100).round(1)
print("Distribucion de clases (%):", dist.to_dict())
print(f"Accuracy de referencia (predecir siempre la clase mayoritaria): {y_test.value_counts(normalize=True).max():.4f}\n")

CONFIGS = [
    ("actual: 100 arboles, sin limite", dict(n_estimators=100)),
    ("100 arboles, max_depth=25", dict(n_estimators=100, max_depth=25)),
    ("100 arboles, max_depth=20", dict(n_estimators=100, max_depth=20)),
    ("100 arboles, max_depth=15", dict(n_estimators=100, max_depth=15)),
    ("50 arboles, max_depth=20", dict(n_estimators=50, max_depth=20)),
    ("100 arboles, min_samples_leaf=5", dict(n_estimators=100, min_samples_leaf=5)),
]

print(f"{'configuracion':36s} {'accuracy':>9s} {'MB':>7s} {'MB zlib':>8s} {'entreno s':>10s}")
for name, params in CONFIGS:
    model = Pipeline([
        ("prep", ColumnTransformer(
            [("cat", OneHotEncoder(handle_unknown="ignore"), ["Wilderness_Area", "Soil_Type"])],
            remainder="passthrough",
        )),
        ("clf", RandomForestClassifier(random_state=42, n_jobs=1, **params)),
    ])
    t0 = time.time()
    model.fit(X_train, y_train)
    secs = time.time() - t0
    acc = accuracy_score(y_test, model.predict(X_test))
    raw = pickle.dumps(model, protocol=4)
    mb, mb_z = len(raw) / 2**20, len(zlib.compress(raw, 6)) / 2**20
    print(f"{name:36s} {acc:9.4f} {mb:7.1f} {mb_z:8.1f} {secs:10.1f}")
