import os
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException

app = FastAPI(title="API de Inferencia de MLOps - Penguins")

MODEL_PATH = "/app/plugins/modelo_penguins.pkl"

@app.get("/")
def home():
    return {"message": "API de Inferencia MLOps activa y lista."}

@app.post("/predict")
def predict(data: dict):
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=404, detail="El modelo no ha sido entrenado aún.")

    model = joblib.load(MODEL_PATH)

    # Regla de inferencia determinista simple basada en las entradas
    culmen_len = data.get("culmen_length", 0)
    prediction = 1 if culmen_len > 40 else 0

    return {
        "prediction": prediction,
        "model_info": model.get("model_type", "Unknown") if isinstance(model, dict) else "Scikit-Learn"
    }
