import json
import os
import threading
from dataclasses import dataclass
from typing import Optional

import joblib

MODELS_DIR = os.environ.get("MODELS_DIR", "/models")


@dataclass
class LoadedModel:
    model: object
    model_file: str
    mtime: float
    metadata: dict


class ModelRegistry:
    def __init__(self, models_dir: str = MODELS_DIR):
        self.models_dir = models_dir
        self._lock = threading.Lock()
        self._current: Optional[LoadedModel] = None

    def list_model_files(self):
        if not os.path.isdir(self.models_dir):
            return []
        files = [f for f in os.listdir(self.models_dir) if f.endswith(".joblib")]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(self.models_dir, f)))
        return files

    def list_model_files_with_metadata(self):
        files = self.list_model_files()
        result = []
        for f in files:
            meta_path = os.path.join(self.models_dir, f.replace(".joblib", ".json"))
            metadata = {}
            if os.path.isfile(meta_path):
                with open(meta_path) as meta_file:
                    metadata = json.load(meta_file)
            result.append({
                "model_file": f, 
                "accuracy": metadata.get("accuracy"),
                "algorithm": metadata.get("algorithm"),
                "created_at": metadata.get("created_at"),
                })
        return result

    def _latest_file(self):
        files = self.list_model_files()
        return files[-1] if files else None

    def best_by_accuracy(self):
        with_accuracy = [
            f for f in self.list_model_files_with_metadata() if f.get("accuracy") is not None
        ]
        if not with_accuracy:
            return None
        best = max(with_accuracy, key=lambda f: f["accuracy"])
        return best["model_file"]

    def _load(self, filename: str) -> LoadedModel:
        model_path = os.path.join(self.models_dir, filename)
        model = joblib.load(model_path)

        meta_path = os.path.join(self.models_dir, filename.replace(".joblib", ".json"))
        metadata = {}
        if os.path.isfile(meta_path):
            with open(meta_path) as f:
                metadata = json.load(f)

        return LoadedModel(
            model=model,
            model_file=filename,
            mtime=os.path.getmtime(model_path),
            metadata=metadata,
        )

    def load_by_name(self, file_name: str) -> Optional[LoadedModel]:
        if not file_name.endswith(".joblib"):
            file_name = f"{file_name}.joblib"
        if not os.path.isfile(os.path.join(self.models_dir, file_name)):
            return None
        with self._lock:
            self._current = self._load(file_name)
            return self._current

    def refresh_if_needed(self) -> Optional[LoadedModel]:
        """Recarga el modelo si hay un archivo .joblib más nuevo que el
        cargado actualmente, o si aún no se ha cargado ninguno."""
        latest = self._latest_file()
        if latest is None:
            return None

        latest_path = os.path.join(self.models_dir, latest)
        latest_mtime = os.path.getmtime(latest_path)

        with self._lock:
            if (
                self._current is None
                or self._current.model_file != latest
                or self._current.mtime != latest_mtime
            ):
                self._current = self._load(latest)
            return self._current

    def force_reload(self) -> Optional[LoadedModel]:
        with self._lock:
            self._current = None
        return self.refresh_if_needed()

    @property
    def current(self) -> Optional[LoadedModel]:
        with self._lock:
            return self._current


registry = ModelRegistry()
