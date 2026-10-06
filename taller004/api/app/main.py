from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException

from app.model_loader import MODEL_ALIAS, MODEL_NAME, loader
from app.schemas import FEATURE_COLUMNS, PenguinFeatures, PredictResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Intentar cargar el modelo al arrancar, pero NUNCA impedir que la API arranque
    # (puede que todavia no se haya registrado ningun modelo en MLflow).
    try:
        loaded = loader.refresh_if_needed()
        print(f"Modelo inicial: {loaded.name} v{loaded.version}")
    except Exception as exc:
        print(f"No se pudo cargar un modelo al iniciar: {exc}")
    yield


app = FastAPI(title="Taller 4 - API de Inferencia Penguins (MLflow)", lifespan=lifespan)


@app.get("/health")
def health():
    current = loader.current
    return {
        "status": "ok",
        "model": f"{MODEL_NAME}@{MODEL_ALIAS}",
        "model_loaded": current is not None,
        "model_version": current.version if current else None,
    }


@app.post("/reload")
def reload_model():
    try:
        loaded = loader.force_reload()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No se pudo cargar el modelo desde MLflow: {exc}")
    return {"reloaded": True, "model_name": loaded.name, "model_version": loaded.version}


@app.post("/predict", response_model=PredictResponse)
def predict(features: PenguinFeatures):
    X = pd.DataFrame([features.model_dump()])[FEATURE_COLUMNS]
    try:
        species = loader.predict(X)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No hay modelo disponible en MLflow: {exc}")

    current = loader.current
    return PredictResponse(
        species=species,
        model_name=current.name,
        model_version=current.version,
        model_alias=current.alias,
        run_id=current.run_id,
    )
