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

    green_potions_delivered = red_potions_delivered = blue_potions_delivered = 0
    green_ml_used = red_ml_used = blue_ml_used = 0

    for potion in potions_delivered:
        if (potion.potion_type[0] == 1):
            red_potions_delivered = potion.quantity
            red_ml_used = potion.quantity * 100
        elif (potion.potion_type[1] == 1):
            green_potions_delivered = potion.quantity
            green_ml_used = potion.quantity * 100
        elif (potion.potion_type[2] == 1):
            blue_potions_delivered = potion.quantity
            blue_ml_used = potion.quantity * 100

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
                f"""
                UPDATE global_inventory
                SET num_green_ml = num_green_ml - {green_ml_used},
                    num_green_potions = num_green_potions + {green_potions_delivered},
                    num_red_ml = num_red_ml - {red_ml_used},
                    num_red_potions = num_red_potions + {red_potions_delivered},
                    num_blue_ml = num_blue_ml - {blue_ml_used},
                    num_blue_potions = num_blue_potions + {blue_potions_delivered}
                """
        ))

    print(f"GREEN POTIONS DELIVERED:\n {green_potions_delivered}\n")
    print(f"RED POTIONS DELIVERED:\n {red_potions_delivered}\n")
    print(f"BLUE POTIONS DELIVERED:\n {blue_potions_delivered}\n")

    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.

    with db.engine.begin() as connection:
        inventory = connection.execute(sqlalchemy.text(
            """
            SELECT num_green_ml,
                   num_red_ml,
                   num_blue_ml
            FROM global_inventory
            """
        ))
        inventory_dict = inventory.mappings().fetchone()
        num_green_ml = inventory_dict['num_green_ml']
        num_red_ml = inventory_dict['num_red_ml']
        num_blue_ml = inventory_dict['num_blue_ml']

        potions_receipt = []

        green_potions_ordered = red_potions_ordered = blue_potions_ordered = 0

        green_potions_ordered = (num_green_ml // 100)
        red_potions_ordered = (num_red_ml // 100)
        blue_potions_ordered = (num_blue_ml // 100)

        #Create Receipt
        if (red_potions_ordered > 0):
            potions_receipt.append(
                {
                    "potion_type": [1,0,0],
                    "quantity": red_potions_ordered
                }
            )
        if (green_potions_ordered > 0):
            potions_receipt.append(
                {
                    "potion_type": [0,1,0],
                    "quantity": green_potions_ordered
                }
            )
        if (blue_potions_ordered > 0):
            potions_receipt.append(
                {
                    "potion_type": [0,0,1],
                    "quantity": blue_potions_ordered
                }
            )
         
        if (len(potions_receipt) > 0):
                print(f"potions ORDERED:\n {potions_receipt}\n")
                return potions_receipt
    return [
            {
                "potion_type": [],
                "quantity": 0,
            }
        ]

if __name__ == "__main__":
    print(get_bottle_plan())
