from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    description: str


from pydantic import BaseModel, Field


class PenguinFeatures(BaseModel):
    unnamed_0: int = Field(0, alias="Unnamed: 0")
    bill_length_mm: float
    bill_depth_mm: float
    flipper_length_mm: float
    body_mass_g: float
    year: int
    island_Dream: int
    island_Torgersen: int
    sex_male: int

    class Config:
       populate_by_name = True
