from fastapi import FastAPI
from app.metodos import router as metodos_router
from app.respuestas_y_estados import router as respuestas_router

app = FastAPI(
    title="ML Inference API",
    description="Sirve inferencias con el modelo mas reciente entrenado en ml_jupyter/train_model.ipynb",
    version="1.0.0"
)

app.include_router(metodos_router)
app.include_router(respuestas_router)

@app.get("/")
def home():
    return {"message": "¡Hola, FastAPI está funcionando!"}
