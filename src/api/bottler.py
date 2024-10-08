from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    with db.engine.begin() as connection:
        potion_inventory = connection.execute(sqlalchemy.text(
            """
            UPDATE catalog
            SET 
            FROM 
            """
        )).mappings().fetchall()

    

    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    potions_receipt = []

    with db.engine.begin() as connection:
        inventory = connection.execute(sqlalchemy.text(
            """
            SELECT num_green_ml,
                   num_red_ml,
                   num_blue_ml
            FROM global_inventory
            """
        )).mappings().fetchone()
        num_green_ml = inventory['num_green_ml']
        num_red_ml = inventory['num_red_ml']
        num_blue_ml = inventory['num_blue_ml']

        potion_inventory = connection.execute(sqlalchemy.text(
            """
            SELECT sku,
                   name,
                   red,
                   green,
                   blue,
                   dark
            FROM catalog
            WHERE sku = 'RED_POTION_0' OR sku = 'GREEN_POTION_0' OR sku = 'BLUE_POTION_0' 
            """
        )).mappings().fetchall()

        print(potion_inventory)

        while num_red_ml != 0 and num_green_ml != 0 and num_blue_ml != 0:
            for potion in potion_inventory:
                if potion['red'] <= num_red_ml and potion['green'] <= num_green_ml and potion['blue'] <= num_blue_ml:
                    num_producable = min(min(num_red_ml // potion['red'], num_green_ml // potion['green']), num_blue_ml // potion['blue'])
                    potions_receipt.append(
                        {
                            "potion_type": [potion['red'], potion['green'], potion['blue'], potion['dark']],
                            "quantity": 1
                        }
                    )
                    num_red_ml -= potion['red']
                    num_green_ml -= potion['green']
                    num_blue_ml -= potion['blue']
        
        connection.execute(sqlalchemy.text(
            f"""
            UPDATE global_inventory
            SET num_red_ml = {num_red_ml},
                num_green_ml = {num_green_ml},
                num_blue_ml = {num_blue_ml}
            """
        ))

        print(f"BOTTLER PLAN: {potions_receipt}")
        return potions_receipt

if __name__ == "__main__":
    print(get_bottle_plan())
