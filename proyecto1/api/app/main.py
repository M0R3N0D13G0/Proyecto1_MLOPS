from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException

from app.model_registry import registry
from app.schemas import CoverTypeFeatures, PredictResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Intentar cargar un modelo al arrancar, pero NUNCA impedir que la API arranque.
    try:
        loaded = registry.refresh_if_needed()
        print(f"Modelo inicial: {loaded.name if loaded else 'ninguno todavia'}")
    except Exception as exc:
        print(f"No se pudo cargar un modelo al iniciar: {exc}")
    yield


app = FastAPI(title="Proyecto 1 - API de Inferencia Covertype (grupo 7)", lifespan=lifespan)


@app.get("/health")
def health():
    current = registry.current
    return {"status": "ok", "model_loaded": current.name if current else None}


@app.get("/models")
def list_models():
    current = registry.current
    return {
        "available_models": registry.list_models(),
        "current_model": current.name if current else None,
    }


@app.post("/reload")
def reload_model():
    loaded = registry.force_reload()
    if loaded is None:
        raise HTTPException(status_code=404, detail="No hay modelos en MinIO todavia.")
    return {"reloaded": True, "model_name": loaded.name}


@app.post("/predict", response_model=PredictResponse)
def predict(features: CoverTypeFeatures):
    try:
        loaded = registry.refresh_if_needed()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No se pudo consultar MinIO: {exc}")
    if loaded is None:
        raise HTTPException(status_code=503, detail="Aun no hay un modelo entrenado en MinIO.")

    X = pd.DataFrame([features.model_dump()])[loaded.metadata["features"]]
    prediction = int(loaded.model.predict(X)[0])

    return PredictResponse(
        prediction=prediction,
        model_name=loaded.name,
        model_accuracy=loaded.metadata.get("accuracy"),
        model_created_at=loaded.metadata.get("created_at"),
    )