from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        inventory = connection.execute(sqlalchemy.text(
                """
                SELECT gold, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, potion_quantity
                FROM global_inventory
                """
        )).mappings().fetchone()

        num_ml = inventory['num_red_ml'] + inventory['num_green_ml'] + inventory['num_blue_ml'] + inventory['num_dark_ml']
        num_potions = inventory['potion_quantity']

    return {"number_of_potions": num_potions, "ml_in_barrels": num_ml, "gold": inventory['gold']}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    with db.engine.begin() as connection:
        capacities = connection.execute(sqlalchemy.text(
            """
            SELECT ml_capacity, potion_capacity, gold
            FROM global_inventory
            """
        )).first()

    purchase_pot = False
    purchase_ml = False
    ml_cap = capacities.ml_capacity
    potion_cap = capacities.potion_capacity
    gold = capacities.gold

    if potion_cap == 50 and gold > 2000:
        purchase_pot = True
    if  ml_cap == 10000 and gold > 5000:
        purchase_ml = True
    if ml_cap == 20000 and potion_cap == 100 and gold >= 15000:
        purchase_pot = True
        purchase_ml = True
    if gold >= 20000:
        purchase_pot = True
        purchase_ml = True
        
    return {
        "potion_capacity": 1 if purchase_pot else 0,
        "ml_capacity": 1 if purchase_ml else 0
        }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    with db.engine.begin() as connection:
        ml_transaction = f"Purchased {capacity_purchase.ml_capacity} ml capacity"
        potion_transaction = f"Purchased {capacity_purchase.potion_capacity} potion capacity"

        connection.execute(sqlalchemy.text(
            """
            -- We put ml in barrels so this makes sense.
            INSERT INTO barrel_transactions (sku, quantity, gold_spent, transaction)
            VALUES ('ml_capacity', :ml_cap_purchased, :ml_gold_spent, :ml_transaction);

            -- We put potions in barrels so this makes sense.
            INSERT INTO barrel_transactions (sku, quantity, gold_spent, transaction)
            VALUES ('potion_capacity', :potion_cap_purchased, :potion_gold_spent, :potion_transaction);

            UPDATE global_inventory 
            SET ml_capacity = ml_capacity + (10000*:ml_cap_purchased),
                potion_capacity = potion_capacity + (50*:potion_cap_purchased),
                gold = 100 + 
                    (SELECT CASE WHEN EXISTS (SELECT 1 FROM barrel_transactions)
                        THEN (SELECT SUM(gold_spent) FROM barrel_transactions)
                        ELSE 0
                        END
                    ) +
                    (SELECT CASE WHEN EXISTS (SELECT 1 FROM cart_items)
                        THEN (SELECT SUM(gold) FROM cart_items)
                        ELSE 0
                        END
                    ) 
            
            """
        ),
            {
                'ml_cap_purchased': capacity_purchase.ml_capacity,
                'potion_cap_purchased': capacity_purchase.potion_capacity,
                'ml_gold_spent': capacity_purchase.ml_capacity * -1000,
                'potion_gold_spent': capacity_purchase.potion_capacity * -1000,
                'ml_transaction': ml_transaction,
                'potion_transaction': potion_transaction
            }
        )

    return "OK"
