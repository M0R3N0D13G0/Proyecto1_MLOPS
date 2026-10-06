from typing import Optional

from pydantic import BaseModel, Field


class CoverTypeFeatures(BaseModel):
    Elevation: float
    Aspect: float
    Slope: float
    Horizontal_Distance_To_Hydrology: float
    Vertical_Distance_To_Hydrology: float
    Horizontal_Distance_To_Roadways: float
    Hillshade_9am: float = Field(..., ge=0, le=255)
    Hillshade_Noon: float = Field(..., ge=0, le=255)
    Hillshade_3pm: float = Field(..., ge=0, le=255)
    Horizontal_Distance_To_Fire_Points: float
    Wilderness_Area: str
    Soil_Type: str

    # Ejemplo tomado de una fila REAL de la API del profesor (sale prellenado en /docs)
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "Elevation": 3142, "Aspect": 59, "Slope": 14,
                "Horizontal_Distance_To_Hydrology": 421,
                "Vertical_Distance_To_Hydrology": 61,
                "Horizontal_Distance_To_Roadways": 1471,
                "Hillshade_9am": 230, "Hillshade_Noon": 210, "Hillshade_3pm": 110,
                "Horizontal_Distance_To_Fire_Points": 3415,
                "Wilderness_Area": "Commanche", "Soil_Type": "C7757",
            }]
        }
    }


class PredictResponse(BaseModel):
    prediction: int
    model_name: str
    model_accuracy: Optional[float] = None
    model_created_at: Optional[str] = None