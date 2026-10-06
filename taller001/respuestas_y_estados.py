from fastapi import APIRouter, HTTPException
import pandas as pd
from modelo_de_datos import PenguinFeatures
from carga_modelo import cargar_modelos

router = APIRouter()
modelos = cargar_modelos()

def construir_dataframe(datos: PenguinFeatures):
    return pd.DataFrame([datos.dict(by_alias=True)])

@router.post("/predict")
def predict_species(datos: PenguinFeatures):
    if "decision_tree" not in modelos:
        raise HTTPException(status_code=500, detail="Modelo principal no cargado.")
    
    input_data = construir_dataframe(datos)
    prediccion = modelos["decision_tree"].predict(input_data)
    return {
        "selected_model": "Decision Tree (Default)",
        "predicted_species": str(prediccion[0])
    }

@router.post("/predict/{nombre_modelo}")
def predict_species_por_modelo(nombre_modelo: str, datos: PenguinFeatures):
    clave = nombre_modelo.lower()
    if clave not in modelos:
        raise HTTPException(
            status_code=400, 
            detail=f"Modelo no disponible. Opciones válidas: {list(modelos.keys())}"
        )
    
    input_data = construir_dataframe(datos)
    prediccion = modelos[clave].predict(input_data)
    return {
        "selected_model": clave,
        "predicted_species": str(prediccion[0])
    }
