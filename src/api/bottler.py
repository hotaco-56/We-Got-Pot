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

    num_red_delivered = 0
    num_green_delivered = 0
    num_blue_delivered = 0

    with db.engine.begin() as connection:
        catalog = connection.execute(sqlalchemy.text(
            """
            SELECT sku, name, red, green, blue, dark
            FROM catalog
            WHERE sku IN ('RED_POTION_0', 'GREEN_POTION_0', 'BLUE_POTION_0')
            """
        )).mappings().fetchall()

        for potion in potions_delivered:
            for sku in catalog:
                if sku['red'] == potion.potion_type[0] and sku['green'] == potion.potion_type[1] and sku['blue'] == potion.potion_type[3] and sku['dark'] == potion.potion_type[3]:
                    match sku['sku']:
                        case 'RED_POTION_0':
                            num_red_delivered += potion.quantity
                        case 'GREEN_POTION_0':
                            num_green_delivered += potion.quantity
                        case 'BLUE_POTION_0':
                            num_blue_delivered += potion.quantity

        connection.execute(sqlalchemy.text(
            f"""
            UPDATE catalog
            SET quantity = CASE sku
            WHEN 'RED_POTION_0' THEN quantity + {num_red_delivered}
            WHEN 'GREEN_POTION_0' THEN quantity + {num_green_delivered}
            WHEN 'BLUE_POTION_0' THEN quantity + {num_blue_delivered}
            ELSE quantity
            END
            WHERE sku IN ('RED_POTION_0', 'GREEN_POTION_0', 'BLUE_POTION_0')
            """
        ))

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
            WHERE sku IN ('RED_POTION_0', 'GREEN_POTION_0', 'BLUE_POTION_0')
            """
        )).mappings().fetchall()

        while num_red_ml != 0 or num_green_ml != 0 or num_blue_ml != 0:
            for potion in potion_inventory:
                if potion['red'] <= num_red_ml and potion['green'] <= num_green_ml and potion['blue'] <= num_blue_ml:
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
