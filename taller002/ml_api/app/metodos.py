from fastapi import APIRouter, HTTPException

router = APIRouter()

items = {
    "1": "Laptop",
    "2": "Teléfono"
}

@router.get("/items/{item_id}")
def get_item(item_id: str):

    if item_id not in items:
        raise HTTPException(
            status_code=404,
            detail="Item no encontrado"
        )

    return {
        "item_id": item_id,
        "name": items[item_id]
    }

@router.post("/items/")
def create_item(name: str):
    return {
        "name": name,
        "message": "El item ha sido creado"
    }


@router.put("/items/{item_id}")
def update_item(item_id: int, name: str):
    return {
        "item_id": item_id,
        "name": name,
        "message": "Item actualizado"
    }


@router.delete("/items/{item_id}")
def delete_item(item_id: int):
    return {
        "message": f"Item {item_id} eliminado"
    }
