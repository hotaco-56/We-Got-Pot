from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src.api import info
from src.api import helper

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

    with db.engine.begin() as connection:
        for barrel in barrels_delivered:
            red_ml_delivered = green_ml_delivered = blue_ml_delivered = dark_ml_delivered = 0
        
            if (barrel.potion_type[0] == 1):
                red_ml_delivered = barrel.ml_per_barrel * barrel.quantity
            elif (barrel.potion_type[1] == 1):
                green_ml_delivered = barrel.ml_per_barrel * barrel.quantity
            elif (barrel.potion_type[2] == 1):
                blue_ml_delivered = barrel.ml_per_barrel * barrel.quantity
            elif (barrel.potion_type[3] == 1):
                dark_ml_delivered = barrel.ml_per_barrel * barrel.quantity

            transaction = f"Purchased {barrel.quantity} {barrel.sku} for {barrel.price * barrel.quantity}"

            connection.execute(sqlalchemy.text(
                """
                INSERT INTO barrel_transactions (sku, quantity, transaction, gold_spent)
                VALUES (
                    :sku,
                    :quantity,
                    :transaction,
                    :gold_spent
                );

                INSERT INTO ml_transactions (transaction, red, green, blue, dark)
                VALUES (
                    :transaction,
                    :red,
                    :green,
                    :blue,
                    :dark
                );
                """
            ),
                {
                    'sku': barrel.sku,
                    'quantity': barrel.quantity,
                    'gold_spent': -(barrel.price * barrel.quantity),
                    'transaction': transaction,
                    'red': red_ml_delivered,
                    'green': green_ml_delivered,
                    'blue': blue_ml_delivered,
                    'dark': dark_ml_delivered,
                }
            )

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
                f"""
                UPDATE global_inventory
                SET num_red_ml = (SELECT SUM(red) FROM ml_transactions),
                    num_green_ml = (SELECT SUM(green) FROM ml_transactions),
                    num_blue_ml = (SELECT SUM(blue) FROM ml_transactions),
                    num_dark_ml = (SELECT SUM(dark) FROM ml_transactions),
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
        ))

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    barrel_receipt_dict = {
        'LARGE_RED_BARREL': 0,
        'MEDIUM_RED_BARREL': 0,
        'SMALL_RED_BARREL': 0,
        'MINI_RED_BARREL': 0,
        'LARGE_GREEN_BARREL': 0,
        'MEDIUM_GREEN_BARREL': 0,
        'SMALL_GREEN_BARREL': 0,
        'MINI_GREEN_BARREL': 0,
        'LARGE_BLUE_BARREL': 0,
        'MEDIUM_BLUE_BARREL': 0,
        'SMALL_BLUE_BARREL': 0,
        'MINI_BLUE_BARREL': 0,
        'LARGE_DARK_BARREL': 0
    }
    barrels_receipt = []
    bottle_plan = []
    inventory = []

    #Parse barrels in roxanne's catalog
    barrel_catalog_dict = {}
    for barrel in wholesale_catalog:
        barrel_catalog_dict[barrel.sku] = barrel.quantity

    print("CATALOG")
    print(barrel_catalog_dict)

    #get current inventory
    with db.engine.begin() as connection:
        inventory = connection.execute(sqlalchemy.text(
            """
            SELECT num_green_ml, 
                   num_red_ml,
                   num_blue_ml,
                   num_dark_ml,
                   gold,
                   ml_capacity,
                   potion_capacity
            FROM global_inventory
            """
        )).mappings().first()

    gold_available = inventory['gold']
    num_red_ml = inventory['num_red_ml']
    num_green_ml = inventory['num_green_ml']
    num_blue_ml = inventory['num_blue_ml']
    num_dark_ml = inventory['num_dark_ml']
    ml_capacity = inventory['ml_capacity']
    total_ml = num_red_ml + num_green_ml + num_blue_ml + num_dark_ml

    if total_ml > 0.5 * ml_capacity:
        print("ending barrel plan, have more than half capacity")
        return barrels_receipt

    # GET PLAN BASED ON CURRENT DAY
    bottle_plan = helper.get_day_plan()

    # CALCULATE ML NEEDED
    red_ml_needed = green_ml_needed = blue_ml_needed = dark_ml_needed = 0
    for potion in bottle_plan:
        #only count potions that we need more of
        if potion['max_quantity'] > potion['quantity']:
            red_ml_needed += potion['red'] * (potion['max_quantity'] - potion['quantity'])
            green_ml_needed += potion['green'] * (potion['max_quantity'] - potion['quantity'])
            blue_ml_needed += potion['blue'] * (potion['max_quantity'] - potion['quantity'])
            dark_ml_needed += potion['dark'] * (potion['max_quantity'] - potion['quantity'])

    red_ml_needed = 0 if red_ml_needed < num_red_ml else red_ml_needed
    green_ml_needed = 0 if green_ml_needed < num_green_ml else green_ml_needed
    blue_ml_needed = 0 if blue_ml_needed < num_blue_ml else blue_ml_needed

    # uhhhhh
    tmp = [] #so i can sort it
    total_ml_needed = red_ml_needed + green_ml_needed + blue_ml_needed + dark_ml_needed
    #ml needed is scaled to capacity
    red_ml_needed = (red_ml_needed/total_ml_needed) * (ml_capacity - total_ml)
    green_ml_needed = (green_ml_needed/total_ml_needed) * (ml_capacity - total_ml)
    blue_ml_needed = (blue_ml_needed/total_ml_needed) * (ml_capacity - total_ml)
    dark_ml_needed = (dark_ml_needed/total_ml_needed) * (ml_capacity - total_ml)
    tmp.append(red_ml_needed)
    tmp.append(green_ml_needed)
    tmp.append(blue_ml_needed)
    tmp.sort()
    tmp.reverse()

    #Set priority based on ml_needed per color
    ml_needed_dict = {} #easier to use
    for amount in tmp:
        if amount == red_ml_needed and 'red' not in ml_needed_dict:
            ml_needed_dict['red'] = red_ml_needed
        elif amount == green_ml_needed and 'green' not in ml_needed_dict:
            ml_needed_dict['green'] = green_ml_needed
        elif amount == blue_ml_needed and 'blue' not in ml_needed_dict:
            ml_needed_dict['blue'] = blue_ml_needed
    #end uhhhhhhhhh

    print(f"TOTAL ML:{total_ml}")
    print(f"Available Capacity: {ml_capacity-total_ml}")
    print("ML_NEEDED")
    print(ml_needed_dict)

    #order barrels based on priority   
    for color, ml_needed in ml_needed_dict.items():
        if ml_needed == 0:
            continue
        print(f"gold for {color} : {gold_available}")
        #wtf
        gold_available = order_barrels(barrel_catalog_dict, barrel_receipt_dict, color, ml_needed, gold_available)

    #create output for api
    for barrel, count in barrel_receipt_dict.items():
        if count > 0:
            barrels_receipt.append({"sku": barrel, "quantity": count})
            
    print(f"BARRELS ORDERED: {barrels_receipt}")
    print(f"gold after orders complete: {gold_available}")
    return barrels_receipt

def order_barrels(barrels: dict, barrel_receipt: dict, color:str, ml_needed:int, gold:int):
    color = color.upper()

    LARGE_ML = 10000
    MEDIUM_ML = 2500
    SMALL_ML = 500
    MINI_ML = 200
    LARGE_DARK_ML_COST = 750
    LARGE_ML_COST = 500 if color != 'BLUE' else 600
    MEDIUM_ML_COST = 250 if color != 'BLUE' else 300
    SMALL_ML_COST = 100 if color != 'BLUE' else 120
    MINI_ML_COST = 60

    num_large = barrels[f'LARGE_{color}_BARREL'] if f'LARGE_{color}_BARREL' in barrels else 0
    num_medium = barrels[f'MEDIUM_{color}_BARREL'] if f'MEDIUM_{color}_BARREL' in barrels else 0
    num_small = barrels[f'SMALL_{color}_BARREL'] if f'SMALL_{color}_BARREL' in barrels else 0
    num_mini = barrels[f'MINI_{color}_BARREL'] if f'MINI_{color}_BARREL' in barrels else 0

    #buy large
    if num_large != 0:
        num_to_buy = int(ml_needed // LARGE_ML) 
        if (num_to_buy > 0):
            if (num_to_buy > num_large):
                num_to_buy = num_large
            if (num_to_buy * LARGE_ML_COST > gold):
                num_to_buy = int(num_large // gold)
            barrel_receipt[f'LARGE_{color}_BARREL'] += int(num_to_buy)
            ml_needed -= num_large * LARGE_ML
            gold -= num_large * LARGE_ML_COST

    #buy medium
    if num_medium != 0:
        num_to_buy = int(ml_needed // MEDIUM_ML) 
        if (num_to_buy > 0):
            if (num_to_buy > num_medium):
                num_to_buy = num_medium
            if (num_to_buy * MEDIUM_ML_COST > gold):
                num_to_buy =  int(num_medium // gold)
            barrel_receipt[f'MEDIUM_{color}_BARREL'] += int(num_to_buy)
            ml_needed -= num_medium * MEDIUM_ML
            gold -= num_medium * MEDIUM_ML_COST
    
    #buy small
    if num_small != 0:
        num_to_buy = int(ml_needed // SMALL_ML) 
        if (num_to_buy > 0):
            if (num_to_buy > num_small):
                num_to_buy = num_small
            if (num_to_buy * SMALL_ML_COST > gold):
                num_to_buy = int(num_small // gold)
            barrel_receipt[f'SMALL_{color}_BARREL'] += int(num_to_buy)
            ml_needed -= num_small * SMALL_ML
            gold -= num_small * SMALL_ML_COST

    #buy MINI
    if num_mini != 0:
        num_to_buy = int(ml_needed // MINI_ML) 
        if (num_to_buy > 0):
            if (num_to_buy > num_mini):
                num_to_buy = num_mini
            if (num_to_buy * MINI_ML_COST > gold):
                num_to_buy = int(num_mini // gold)
            barrel_receipt[f'MINI_{color}_BARREL'] += int(num_to_buy)
            ml_needed -= num_mini * MINI_ML
            gold -= num_mini * MINI_ML_COST
    
    return gold