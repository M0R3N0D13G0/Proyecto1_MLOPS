import os
import threading
from dataclasses import dataclass
from typing import Optional

import mlflow
from mlflow import MlflowClient

import pandas as pd

MLFLOW_TRACKING_URI = os.environ["MLFLOW_TRACKING_URI"]
MODEL_NAME = os.environ["MODEL_NAME"]
MODEL_ALIAS = os.environ["MODEL_ALIAS"]

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

@dataclass
class LoadedModel:
    model: object
    name: str
    version: Optional[str]
    alias: Optional[str]
    run_id: Optional[str]


class MlflowModelLoader:
    """Carga el modelo `MODEL_NAME@MODEL_ALIAS` desde el Model Registry de MLflow.

    Misma idea que ModelRegistry de proyecto1 (cache + lock + recarga cuando cambia
    la version), pero la fuente es MLflow en vez de MinIO directo.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._current: Optional[LoadedModel] = None
        self._client = MlflowClient() 

    def _load(self) -> LoadedModel:
        mv = self._client.get_model_version_by_alias(name=MODEL_NAME, alias=MODEL_ALIAS)
        model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/{mv.version}")
        return LoadedModel(
            model=model,
            name=MODEL_NAME,
            version=mv.version,
            alias=MODEL_ALIAS,
            run_id=mv.run_id,
        )

    def _latest_version(self) -> Optional[str]:
        mv = self._client.get_model_version_by_alias(name=MODEL_NAME, alias=MODEL_ALIAS)
        return mv.version

    def refresh_if_needed(self) -> LoadedModel:
        version = self._latest_version()
        with self._lock:
            if self._current is None or self._current.version != version:
                self._current = self._load()
            return self._current

    def force_reload(self) -> LoadedModel:
        with self._lock:
            self._current = None
        return self.refresh_if_needed()

    def predict(self, X: pd.DataFrame) -> str:
        loaded = self.refresh_if_needed()
        return str(loaded.model.predict(X)[0])

    @property
    def current(self) -> Optional[LoadedModel]:
        return self._current


loader = MlflowModelLoader()
