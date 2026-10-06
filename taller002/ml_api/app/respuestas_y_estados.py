from fastapi import APIRouter, HTTPException

from app.carga_modelo import registry
from app.modelo_de_datos import PredictRequest, PredictResponse

router = APIRouter()


@router.get("/health")
def health():
    current = registry.current
    return {
        "status": "ok",
        "models_dir": registry.models_dir,
        "model_loaded": current.model_file if current else None,
    }


@router.get("/models")
def list_models():
    files = registry.list_model_files_with_metadata()
    current = registry.current
    return {
        "available_models": files,
        "current_model": current.model_file if current else None,
    }


@router.post("/reload")
def reload_model():
    loaded = registry.force_reload()
    if loaded is None:
        raise HTTPException(
            status_code=404,
            detail=f"No hay modelos (.joblib) en {registry.models_dir}. "
            "Entrena uno primero desde el notebook.",
        )
    return {"reloaded": True, "model_file": loaded.model_file}


@router.post("/predict", response_model=PredictResponse)
def predict_species(datos: PredictRequest):
    if datos.model_file:
        try:
            loaded = registry.load_by_name(datos.model_file)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"No existe el modelo '{datos.model_file}' en "
                f"{registry.models_dir}. Usa GET /models para ver los disponibles.",
            )
    else:
        best_file = registry.best_by_accuracy()
        if best_file is None:
            raise HTTPException(
                status_code=404,
                detail=f"No hay modelos con accuracy registrado en "
                f"{registry.models_dir}. Entrena uno desde el notebook.",
            )
        loaded = registry.load_by_name(best_file)

    expected_features = len(loaded.metadata.get("feature_names", []) or [])
    if expected_features and len(datos.features) != expected_features:
        raise HTTPException(
            status_code=422,
            detail=(
                f"El modelo '{loaded.model_file}' espera {expected_features} "
                f"features ({loaded.metadata.get('feature_names')}), "
                f"se recibieron {len(datos.features)}."
            ),
        )

    prediction = int(loaded.model.predict([datos.features])[0])

    target_names = loaded.metadata.get("target_names")
    label = (
        target_names[prediction]
        if target_names and 0 <= prediction < len(target_names)
        else None
    )

    return PredictResponse(
        prediction=prediction,
        prediction_label=label,
        model_file=loaded.model_file,
        model_trained_at=loaded.metadata.get("created_at"),
        model_accuracy=loaded.metadata.get("accuracy")
    )
