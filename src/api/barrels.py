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

    print(f"GREEN ML DELIVERED:\n {green_ml_delivered}\n")
    print(f"RED ML DELIVERED:\n {red_ml_delivered}\n")
    print(f"BLUE ML DELIVERED:\n {blue_ml_delivered}\n")
    print(f"GOLD SPENT:\n {gold_spent}\n")

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

        num_green_potions = inventory_dict['num_green_potions']
        gold_available = inventory_dict['gold']
        num_red_potions = inventory_dict['num_red_potions']
        num_blue_potions = inventory_dict['num_blue_potions']

        red_sku = green_sku = blue_sku = ""
        red_barrels_ordered = green_barrels_ordered = blue_barrels_ordered = 0


        for barrel in wholesale_catalog:
            if (barrel.potion_type[0] == 1 and num_red_potions < 3): #red barrel
                if ((gold_available // barrel.price) > barrel.quantity):
                    red_barrels_ordered = barrel.quantity
                else:
                    red_barrels_ordered = gold_available // barrel.price
                red_sku = barrel.sku
                gold_available -= red_barrels_ordered * barrel.price
                barrels_receipt.append(
                    {
                        "sku": red_sku,
                        "quantity": red_barrels_ordered
                    }
                )

            elif (barrel.potion_type[1] == 1 and num_green_potions < 3): #green barrel
                if ((gold_available // barrel.price) > barrel.quantity):
                    green_barrels_ordered = barrel.quantity
                else:
                    green_barrels_ordered = gold_available // barrel.price
                green_sku = barrel.sku
                gold_available -= green_barrels_ordered * barrel.price
                barrels_receipt.append(
                    {
                        "sku": green_sku,
                        "quantity": green_barrels_ordered
                    }
                )

            elif (barrel.potion_type[2] == 1 and num_blue_potions < 3): #blue barrel
                if ((gold_available // barrel.price) > barrel.quantity):
                    blue_barrels_ordered = barrel.quantity
                else:
                    blue_barrels_ordered = gold_available // barrel.price
                blue_sku = barrel.sku
                gold_available -= blue_barrels_ordered * barrel.price
                barrels_receipt.append(
                    {
                        "sku": blue_sku,
                        "quantity": blue_barrels_ordered
                    }
                )
         
    print(f"BARRELS ORDERED: {barrels_receipt}")
    print(f"GOLD AFTER PURCHASE: {gold_available}")
    return barrels_receipt