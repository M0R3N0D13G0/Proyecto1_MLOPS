from fastapi import FastAPI
from metodos import router as metodos_router
from respuestas_y_estados import router as respuestas_router

app = FastAPI(
    title="API de Penguin",
    description="API para predicción de especies de pingüinos",
    version="1.0.0"
)

app.include_router(metodos_router)
app.include_router(respuestas_router)

@app.get("/")
def home():
    return {"message": "¡Hola, FastAPI está funcionando!"}
