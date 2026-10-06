from typing import Literal, Optional

from pydantic import BaseModel, Field

# Columnas de entrada del modelo, en el MISMO orden y con los MISMOS nombres que
# las columnas de features de processed.penguins (ver el notebook, seccion 3).
FEATURE_COLUMNS = [
    "island",
    "bill_length_mm",
    "bill_depth_mm",
    "flipper_length_mm",
    "body_mass_g",
    "sex",
]


class PenguinFeatures(BaseModel):
    island: Literal["Biscoe", "Dream", "Torgersen"]
    bill_length_mm: float = Field(..., gt=0)
    bill_depth_mm: float = Field(..., gt=0)
    flipper_length_mm: float = Field(..., gt=0)
    body_mass_g: float = Field(..., gt=0)
    sex: Literal["female", "male"]

    # Fila real del dataset (rowid 1, Adelie): sale prellenada en /docs.
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "island": "Torgersen",
                "bill_length_mm": 39.1,
                "bill_depth_mm": 18.7,
                "flipper_length_mm": 181,
                "body_mass_g": 3750,
                "sex": "male",
            }]
        }
    }


class PredictResponse(BaseModel):
    species: str
    model_name: str
    model_version: Optional[str] = None
    model_alias: Optional[str] = None
    run_id: Optional[str] = None
