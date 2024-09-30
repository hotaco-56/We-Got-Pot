from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

num_green_potions = 0

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    with db.engine.begin() as connection:
                result = connection.execute(sqlalchemy.text(
                        """
                        SELECT num_green_potions
                        FROM global_inventory
                        """
                ))
                result_list = result.first()
                num_green_potions = result_list[1]
                
    return [
            {
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": num_green_potions,
                "price": 50,
                "potion_type": [0, 100, 0, 0],
            }
        ]
