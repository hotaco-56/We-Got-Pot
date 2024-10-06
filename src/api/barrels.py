from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    red_ml_delivered = green_ml_delivered = blue_ml_delivered = 0
    gold_spent = 0

    for barrel in barrels_delivered:
        if (barrel.potion_type[0] == 1):
            red_ml_delivered = barrel.ml_per_barrel * barrel.quantity
        elif (barrel.potion_type[1] == 1):
            green_ml_delivered = barrel.ml_per_barrel * barrel.quantity
        elif (barrel.potion_type[2] == 1):
            blue_ml_delivered = barrel.ml_per_barrel * barrel.quantity
        gold_spent += barrel.price * barrel.quantity

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
                f"""
                UPDATE global_inventory
                SET num_green_ml = num_green_ml + {green_ml_delivered},
                    num_red_ml = num_red_ml + {red_ml_delivered},
                    num_blue_ml = num_blue_ml + {blue_ml_delivered},
                    gold = gold - {gold_spent}
                """
        ))

    print(f"GREEN ML DELIVERED: {green_ml_delivered}")
    print(f"RED ML DELIVERED: {red_ml_delivered}")
    print(f"BLUE ML DELIVERED: {blue_ml_delivered}")
    print(f"GOLD SPENT: {gold_spent}")

    return "OK"


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    barrels_receipt = []

    with db.engine.begin() as connection:
        inventory = connection.execute(sqlalchemy.text(
            """
            SELECT num_green_ml, 
                   num_green_potions, 
                   gold,
                   num_red_ml,
                   num_red_potions,
                   num_blue_ml,
                   num_blue_potions
            FROM global_inventory
            """
        ))

        inventory_dict = inventory.mappings().first()
        print(f"INVENTORY: {inventory_dict}")

        blue_ml_wanted = 0
        green_ml_wanted = 0
        red_ml_wanted = 0

        num_green_potions = inventory_dict['num_green_potions']
        gold_available = inventory_dict['gold']
        num_red_potions = inventory_dict['num_red_potions']
        num_blue_potions = inventory_dict['num_blue_potions']

        red_sku = green_sku = blue_sku = ""
        red_barrels_ordered = green_barrels_ordered = blue_barrels_ordered = 0

        for barrel in wholesale_catalog:
            if barrel.sku == "MINI_RED_BARREL":
                if gold_available >= barrel.price:
                    barrels_receipt.append(
                        {
                            "sku": barrel.sku,
                            "quantity": 1
                        }
                    )
                    gold_available -= barrel.price
            if barrel.sku == "MINI_GREEN_BARREL":
                if gold_available >= barrel.price:
                    barrels_receipt.append(
                        {
                            "sku": barrel.sku,
                            "quantity": 1
                        }
                    )
                    gold_available -= barrel.price
            elif barrel.sku == "MINI_BLUE_BARREL":
                if gold_available >= barrel.price:
                    barrels_receipt.append(
                        {
                            "sku": barrel.sku,
                            "quantity": 1
                        }
                    )
                    gold_available -= barrel.price

         
    print(f"BARRELS ORDERED: {barrels_receipt}")
    print(f"GOLD AFTER PURCHASE: {gold_available}")
    return barrels_receipt
