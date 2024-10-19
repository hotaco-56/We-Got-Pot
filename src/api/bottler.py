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
    num_green_blue_delivered = 0
    num_blue_red_delivered = 0
    num_red_blue_delivered = 0
    num_green_red_delivered = 0
    num_red_green_delivered = 0

    red_ml_used = 0
    green_ml_used = 0
    blue_ml_used = 0

    with db.engine.begin() as connection:
        catalog = connection.execute(sqlalchemy.text(
            """
            SELECT sku, name, red, green, blue, dark
            FROM catalog
            WHERE sku IN ('RED_POTION', 'GREEN_POTION', 'BLUE_POTION', 'BLUE_RED', 'RED_BLUE')
            """
        )).mappings().fetchall()

        for potion in potions_delivered:
            red_ml = potion.potion_type[0]
            green_ml = potion.potion_type[1]
            blue_ml = potion.potion_type[2]
            dark_ml = potion.potion_type[3]
            for sku in catalog:
                if sku['red'] == red_ml and sku['green'] == green_ml and sku['blue'] == blue_ml and sku['dark'] == dark_ml:
                    match sku['sku']:
                        case 'RED_POTION':
                            num_red_delivered += potion.quantity
                            red_ml_used += red_ml
                        case 'GREEN_POTION':
                            num_green_delivered += potion.quantity
                            green_ml_used += green_ml
                        case 'BLUE_POTION':
                            num_blue_delivered += potion.quantity
                            blue_ml_used += blue_ml
                        case 'BLUE_RED':
                            num_blue_red_delivered += potion.quantity
                            blue_ml_used += blue_ml
                            red_ml_used += red_ml
                        case 'RED_BLUE':
                            num_red_blue_delivered += potion.quantity
                            blue_ml_used += blue_ml
                            red_ml_used += red_ml
                        case 'GREEN_RED':
                            num_green_red_delivered += potion.quantity
                            green_ml_used += green_ml
                            red_ml_used += red_ml
                        case 'RED_GREEN':
                            num_red_green_delivered += potion.quantity
                            red_ml_used += red_ml
                            green_ml_used += green_ml


        connection.execute(sqlalchemy.text(
            f"""
            UPDATE catalog
            SET quantity = CASE sku
            WHEN 'RED_POTION' THEN quantity + {num_red_delivered}
            WHEN 'GREEN_POTION' THEN quantity + {num_green_delivered}
            WHEN 'BLUE_POTION' THEN quantity + {num_blue_delivered}
            WHEN 'BLUE_RED' THEN quantity + {num_blue_red_delivered}
            WHEN 'RED_BLUE' THEN quantity + {num_red_blue_delivered}
            ELSE quantity
            END
            WHERE sku IN ('RED_POTION', 'GREEN_POTION', 'BLUE_POTION', 'BLUE_RED', 'RED_BLUE');

            UPDATE global_inventory
            SET num_red_ml = num_red_ml - {red_ml_used},
                num_green_ml = num_green_ml - {green_ml_used},
                num_blue_ml = num_blue_ml - {blue_ml_used}

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
                   num_blue_ml,
                   num_dark_ml
            FROM global_inventory
            """
        )).mappings().fetchone()
        num_green_ml = inventory['num_green_ml']
        num_red_ml = inventory['num_red_ml']
        num_blue_ml = inventory['num_blue_ml']
        num_dark_ml = inventory['num_dark_ml']

        # BOTTLER PLAN
        potion_inventory = connection.execute(sqlalchemy.text(
            """
            SELECT sku,
                   name,
                   red,
                   green,
                   blue,
                   dark
            FROM catalog 
            WHERE sku IN ('RED_POTION', 'BLUE_POTION', 'RED_GREEN', 'GREEN_RED')
            """
        )).mappings().fetchall()

        while num_red_ml != 0 or num_green_ml != 0 or num_blue_ml != 0:
            potions_ordered = 0
            for potion in potion_inventory:
                if potion['red'] <= num_red_ml and potion['green'] <= num_green_ml and potion['blue'] <= num_blue_ml and potion['dark'] <= num_dark_ml:
                    potions_receipt.append(
                        {
                            "potion_type": [potion['red'], potion['green'], potion['blue'], potion['dark']],
                            "quantity": 1
                        }
                    )
                    num_red_ml -= potion['red']
                    num_green_ml -= potion['green']
                    num_blue_ml -= potion['blue']
                    potions_ordered += 1
            if potions_ordered == 0:
                break

        print(f"BOTTLER PLAN: {potions_receipt}")
        print(f"red used: {inventory['num_red_ml'] - num_red_ml}")
        print(f"green used: {inventory['num_green_ml'] - num_green_ml}")
        print(f"blue used: {inventory['num_blue_ml'] - num_blue_ml}")
        return potions_receipt


if __name__ == "__main__":
    print(get_bottle_plan())
