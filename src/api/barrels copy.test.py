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

def determine_cheapest(barrels: list[Barrel], ml_wanted: int, gold_available):
    for barrel in barrels:
        if barrel.ml_per_barrel > ml_wanted:

    return []

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    barrels_receipt = [Barrel]
    red_barrels = [Barrel]
    green_barrels = [Barrel]
    blue_barrels = [Barrel]
    dark_barrels = [Barrel]

    blue_ml_wanted = 100 
    green_ml_wanted = 100 
    red_ml_wanted = 100
    dark_ml_wanted = 0

    with db.engine.begin() as connection:
        inventory = connection.execute(sqlalchemy.text(
            """
            SELECT gold, 
                   num_red_ml, 
                   num_blue_ml, 
                   num_green_ml,
            FROM global_inventory
            """
        ))

        inventory_dict = inventory.mappings().first()
    print(f"INVENTORY: {inventory_dict}")

    for barrel in wholesale_catalog:
        if barrel.potion_type[0] == 1:
            red_barrels.append(barrel)
        elif barrel.potion_type[1] == 1:
            green_barrels.append(barrel)
        elif barrel.potion_type[2] == 1:
            blue_barrels.append(barrel)
        elif barrel.potion_type[3] == 1:
            dark_barrels.append[barrel]
         
    print(f"BARRELS ORDERED: {barrels_receipt}")
    return barrels_receipt