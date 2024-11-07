from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src.api import info

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
    red_ml_used = 0
    green_ml_used = 0
    blue_ml_used = 0
    dark_ml_used = 0

    with db.engine.begin() as connection:
        potions_inventory = connection.execute(sqlalchemy.text(
            """
            SELECT sku, name, red, green, blue, dark, quantity
            FROM potions
            """
        )).mappings().fetchall()

        potions_delivered_dict = {}

        #loop through delivered potions
        for potion in potions_delivered:
            red_ml = potion.potion_type[0]
            green_ml = potion.potion_type[1]
            blue_ml = potion.potion_type[2]
            dark_ml = potion.potion_type[3]

            #match to sku in database and add to dict
            for sku in potions_inventory:
                if red_ml == sku['red'] and green_ml == sku['green'] and blue_ml == sku['blue'] and dark_ml == sku['dark']:
                    potions_delivered_dict[sku['sku']] = potion.quantity
                    red_ml_used += (red_ml * potion.quantity)
                    green_ml_used += (green_ml * potion.quantity)
                    blue_ml_used += (blue_ml * potion.quantity)
                    dark_ml_used += (dark_ml * potion.quantity)

                    transaction = f"{potion.quantity} {sku['sku']} delivered"

                    connection.execute(sqlalchemy.text(
                        """
                        INSERT INTO potion_transactions (sku, transaction, quantity) 
                        VALUES (
                            :sku,
                            :transaction,
                            :quantity
                        );

                        INSERT INTO ml_transactions (transaction, red, green, blue, dark)
                        VALUES (
                            :transaction,
                            :red,
                            :green,
                            :blue,
                            :dark
                        );

                        UPDATE potions
                        SET quantity = quantity + :quantity
                        WHERE sku = :sku;

                        """
                    ),
                        {
                            'sku': sku['sku'],
                            'transaction': transaction,
                            'quantity': potion.quantity,
                            'red': -sku['red'] * potion.quantity,
                            'green': -sku['green'] * potion.quantity,
                            'blue': -sku['blue'] * potion.quantity,
                            'dark': -sku['dark'] * potion.quantity
                        }
                    )

        #update mls and potion quant
        connection.execute(sqlalchemy.text(
           f"""
            UPDATE global_inventory
            SET num_red_ml = 
                    (SELECT CASE WHEN EXISTS (SELECT 1 FROM ml_transactions)
                        THEN (SELECT SUM(red) FROM ml_transactions)
                        ELSE 0
                        END
                    ),
                num_green_ml = 
                    (SELECT CASE WHEN EXISTS (SELECT 1 FROM ml_transactions)
                        THEN (SELECT SUM(green) FROM ml_transactions)
                        ELSE 0
                        END
                    ),
                num_blue_ml = 
                    (SELECT CASE WHEN EXISTS (SELECT 1 FROM ml_transactions)
                        THEN (SELECT SUM(blue) FROM ml_transactions)
                        ELSE 0
                        END
                    ),
                num_dark_ml = 
                    (SELECT CASE WHEN EXISTS (SELECT 1 FROM ml_transactions)
                        THEN (SELECT SUM(dark) FROM ml_transactions)
                        ELSE 0
                        END
                    ),
                potion_quantity = (SELECT SUM(quantity) FROM potion_transactions)
            """
        ))
        print(f"POTIONS DELIVERED: {potions_delivered_dict}")
        print(f"red used: {red_ml_used}")
        print(f"green used: {green_ml_used}")
        print(f"blue used: {blue_ml_used}")

    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    print("CREATING BOTTLE PLAN")
    potions_receipt = []

    with db.engine.begin() as connection:
        inventory = connection.execute(sqlalchemy.text(
            """
            SELECT num_green_ml,
                   num_red_ml,
                   num_blue_ml,
                   num_dark_ml,
                   potion_capacity,
                   potion_quantity
            FROM global_inventory
            """
        )).mappings().fetchone()

        num_green_ml = inventory['num_green_ml']
        num_red_ml = inventory['num_red_ml']
        num_blue_ml = inventory['num_blue_ml']
        num_dark_ml = inventory['num_dark_ml']
        potion_capacity = inventory['potion_capacity']
        potion_quantity = inventory['potion_quantity']
    
        print(f"INVENTORY: {inventory}")

        bottle_plan_day = info.current_time.day

        # Check if near end of day
        if info.current_time.hour == 22:
            #Set to next day
            bottle_plan_day = info.days_of_week[(info.days_of_week.index(info.current_time.day) + 1) % len(info.days_of_week)]
            print(f"end of day!!! switchting plan! to {bottle_plan_day}")

        match bottle_plan_day:
            case 'Edgeday':
                print("Using edgeday bottler plan")
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM edgeday_plan
                    JOIN potions
                    ON potions.sku = edgeday_plan.potion_sku
                    ORDER BY max_quantity
                    """
                )).mappings().fetchall()
            case 'Blesseday':
                print("Using blesseday bottler plan")
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM blesseday_plan
                    JOIN potions
                    ON potions.sku = blesseday_plan.potion_sku
                    ORDER BY max_quantity
                    """
                )).mappings().fetchall()
            case 'Soulday':
                print("Using soulday bottler plan")
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM soulday_plan
                    JOIN potions
                    ON potions.sku = soulday_plan.potion_sku
                    ORDER BY max_quantity
                    """
                )).mappings().fetchall()
            case 'Bloomday':
                print("Using bloomday bottler plan")
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM bloomday_plan
                    JOIN potions
                    ON potions.sku = bloomday_plan.potion_sku
                    ORDER BY max_quantity
                    """
                )).mappings().fetchall()
            case 'Soulday':
                print("Using Soulday bottler plan")
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM soulday_plan
                    JOIN potions
                    ON potions.sku = soulday_plan.potion_sku
                    ORDER BY max_quantity
                    """
                )).mappings().fetchall()
            case _:
                print("Using gods plan")
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM gods_plan
                    JOIN potions
                    ON potions.sku = gods_plan.potion_sku
                    ORDER BY max_quantity DESC
                    """
                )).mappings().fetchall()

        num_potions_ordered_dict = {}

        for potion in bottle_plan:
            num_potions_ordered_dict[potion['sku']] = 0

        #orders potions based on plan
        #keeps running while still have ml
        #stops running if didn't order any potions
        #                 
        can_order_potions = True
        while can_order_potions:
            potions_ordered = 0
            for potion in bottle_plan:
                enough_ml = potion['red'] <= num_red_ml and potion['green'] <= num_green_ml and potion['blue'] <= num_blue_ml and potion['dark'] <= num_dark_ml
                enough_capacity = potion_quantity < potion_capacity
                if  enough_ml and enough_capacity:

                    if num_potions_ordered_dict[potion['sku']] >= potion['max_quantity']:
                        continue

                    #add to potions ordered
                    num_potions_ordered_dict[potion['sku']] += 1

                    #get ml used
                    num_red_ml -= potion['red']
                    num_green_ml -= potion['green']
                    num_blue_ml -= potion['blue']
                    #update potions amount
                    potions_ordered += 1
                    potion_quantity += 1

            if potions_ordered == 0:
                can_order_potions = False

        #create receipt to return
        for potion in bottle_plan:
            if num_potions_ordered_dict[potion['sku']] > 0:
                potions_receipt.append(
                    {
                        "potion_type": [potion['red'], potion['green'], potion['blue'], potion['dark']],
                        "quantity": num_potions_ordered_dict[potion['sku']]
                    }
                )

        print(f"BOTTLER PLAN: {num_potions_ordered_dict}")
        if potion_quantity == potion_capacity:
            print("POTION CAPACITY REACHED!!!!")
        return potions_receipt


if __name__ == "__main__":
    print(get_bottle_plan())
