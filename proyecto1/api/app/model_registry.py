import io
import json
import os
import threading
from dataclasses import dataclass
from typing import Optional

import joblib
from minio import Minio

MINIO_ENDPOINT = os.environ["MINIO_ENDPOINT"]
MINIO_ROOT_USER = os.environ["MINIO_ROOT_USER"]
MINIO_ROOT_PASSWORD = os.environ["MINIO_ROOT_PASSWORD"]
MINIO_BUCKET = os.environ["MINIO_BUCKET"]


@dataclass
class LoadedModel:
    model: object
    name: str
    metadata: dict


class ModelRegistry:
    def __init__(self):
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ROOT_USER,
            secret_key=MINIO_ROOT_PASSWORD,
            secure=False,
        )
        self.bucket = MINIO_BUCKET
        self._lock = threading.Lock()
        self._current: Optional[LoadedModel] = None

    def _read_bytes(self, key: str) -> bytes:
        response = self.client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def _model_names(self) -> list[str]:
        # El .json es el "commit": solo cuentan los modelos con metadatos completos.
        names = [
            obj.object_name[: -len(".json")]
            for obj in self.client.list_objects(self.bucket)
            if obj.object_name.endswith(".json")
        ]
        return sorted(names)  # el nombre lleva la hora UTC -> orden cronologico

    def list_models(self) -> list[dict]:
        return [json.loads(self._read_bytes(f"{n}.json")) for n in self._model_names()]

    def _load(self, name: str) -> LoadedModel:
        metadata = json.loads(self._read_bytes(f"{name}.json"))
        model = joblib.load(io.BytesIO(self._read_bytes(metadata["model_file"])))
        return LoadedModel(model=model, name=name, metadata=metadata)

    def refresh_if_needed(self) -> Optional[LoadedModel]:
        names = self._model_names()
        if not names:
            return None
        latest = names[-1]
        with self._lock:
            if self._current is None or self._current.name != latest:
                self._current = self._load(latest)
            return self._current

    def force_reload(self) -> Optional[LoadedModel]:
        with self._lock:
            self._current = None
        return self.refresh_if_needed()

    @property
    def current(self) -> Optional[LoadedModel]:
        return self._current


registry = ModelRegistry()