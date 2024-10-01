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

    num_ml_delivered = 0
    gold_spent = 0
    for barrel in barrels_delivered:
        num_ml_delivered += barrel.ml_per_barrel
        gold_spent += barrel.price


    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
                f"""
                UPDATE global_inventory
                SET num_green_ml = num_green_ml + {num_ml_delivered},
                gold = {gold_spent}
                """
        ))

    return "OK"

small_green_barrel_quantity = 0

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    barrels_ordered = 0

    with db.engine.begin() as connection:
        inventory = connection.execute(sqlalchemy.text(
            """
            SELECT num_green_ml, num_green_potions, gold
            FROM global_inventory
            """
        ))
        inventory_list = inventory.first()
        num_green_potions = inventory_list[1]
        gold = inventory_list[2]

        if (num_green_potions < 10):
                for barrel in wholesale_catalog:
                        for i in range(barrel.quantity):
                                if (barrel.potion_type[1] == 1 and barrel.price <= gold):
                                        barrels_ordered += 1
         
        if (barrels_ordered > 0):
                return [
                {
                        "sku": "SMALL_GREEN_BARREL",
                        "quantity": barrels_ordered,
                }
        ] 

    return [
        {
            "sku": [],
            "quantity": [],
        }
    ]
