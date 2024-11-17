from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src.api import info

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
    print(wholesale_catalog)
    barrels_receipt = []
    bottle_plan = []
    inventory = []

    with db.engine.begin() as connection:
        inventory = connection.execute(sqlalchemy.text(
            """
            SELECT num_green_ml, 
                   num_red_ml,
                   num_blue_ml,
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
        ml_capacity = inventory['ml_capacity']
        potion_capacity = inventory['potion_capacity']
        total_ml = num_red_ml + num_green_ml + num_blue_ml

        if (total_ml + 200) > ml_capacity:
            print("NEAR OR AT ML CAPACITY ENDING BARREL PLAN")
            return barrels_receipt

        bottle_plan_day = info.current_time.day

        # Check if near end of day
        if info.current_time.hour == 20:
            #Set to next day
            bottle_plan_day = info.days_of_week[(info.days_of_week.index(info.current_time.day) + 1) % len(info.days_of_week)]
            print(f"end of day!!! switchting plan! to {bottle_plan_day}")

        match bottle_plan_day:
            case 'Edgeday':
                print("Using edgeday barrel plan")
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM edgeday_plan
                    JOIN potions
                    ON potions.sku = edgeday_plan.potion_sku
                    """
                )).mappings().fetchall()
            case 'Blesseday':
                print("Using blesseday barrel plan")
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM blesseday_plan
                    JOIN potions
                    ON potions.sku = blesseday_plan.potion_sku
                    """
                )).mappings().fetchall()
            case 'Arcanaday':
                print("Using arcanaday barrel plan")
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM arcanaday_plan
                    JOIN potions
                    ON potions.sku = arcanaday_plan.potion_sku
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
            case 'Crownday':
                print("Using Crownday bottler plan")
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM crownday_plan
                    JOIN potions
                    ON potions.sku = crownday_plan.potion_sku
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
                    """
                )).mappings().fetchall()

        red_ml_needed = green_ml_needed = blue_ml_needed = dark_ml_needed = 0
        for potion in bottle_plan:
            #only count potions that we need more of
            if potion['max_quantity'] > potion['quantity']:
                red_ml_needed += potion['red'] * (potion['max_quantity'] - potion['quantity'])
                green_ml_needed += potion['green'] * (potion['max_quantity'] - potion['quantity'])
                blue_ml_needed += potion['blue'] * (potion['max_quantity'] - potion['quantity'])

        ml_needed_list = []

        #Check if more is needed
        if red_ml_needed * 1.5 < num_red_ml:
            red_ml_needed  = 0
        else:
            ml_needed_list.append(red_ml_needed)

        if green_ml_needed * 1.5 < num_green_ml:
            green_ml_needed  = 0
        else:
            ml_needed_list.append(green_ml_needed)

        if blue_ml_needed * 1.5 < num_blue_ml:
            blue_ml_needed  = 0
        else:
            ml_needed_list.append(blue_ml_needed)

        print(f"INVENTORY: {inventory}")
        print(f"red ml needed : {red_ml_needed}")
        print(f"green ml needed : {green_ml_needed}")
        print(f"blue ml needed : {blue_ml_needed}")

        total_ml_needed = red_ml_needed + green_ml_needed + blue_ml_needed
        if total_ml_needed == 0:
            print("NO ML NEEDED ENDING BARREL PLAN")
            return barrels_receipt

        ml_needed_list.sort()
        ml_needed_list.reverse()

        print(ml_needed_list)

        #Set priority based on ml_needed per color
        ml_priority_list = []

        for amount in ml_needed_list:
            if amount == red_ml_needed and ml_priority_list.count('red') == 0:
                ml_priority_list.append('red')
            elif amount == green_ml_needed and ml_priority_list.count('green') == 0:
                ml_priority_list.append('green')
            elif amount == blue_ml_needed and ml_priority_list.count('blue') == 0:
                ml_priority_list.append('blue')

        print(f"ML priority : {ml_priority_list}")

        num_large_red = num_small_red = num_med_red = num_mini_red = 0
        num_large_green = num_small_green = num_med_green = num_mini_green = 0
        num_large_blue = num_small_blue = num_med_blue = num_mini_blue = 0

        barrel_catalog_dict = {}

        #Parse barrels in roxanne's catalog
        for barrel in wholesale_catalog:
            match barrel.ml_per_barrel:
                case 200:
                    if barrel.potion_type[0] == 1:
                        barrel_catalog_dict['MINI_RED_BARREL'] = barrel.quantity
                        num_mini_red = barrel.quantity
                    elif barrel.potion_type[1] == 1:
                        barrel_catalog_dict['MINI_GREEN_BARREL'] = barrel.quantity
                        num_mini_green = barrel.quantity
                    elif barrel.potion_type[2] == 1:
                        barrel_catalog_dict['MINI_BLUE_BARREL'] = barrel.quantity
                        num_mini_blue = barrel.quantity
                case 500:
                    if barrel.potion_type[0] == 1:
                        barrel_catalog_dict['SMALL_RED_BARREL'] = barrel.quantity
                        num_small_red = barrel.quantity
                    elif barrel.potion_type[1] == 1:
                        barrel_catalog_dict['SMALL_GREEN_BARREL'] = barrel.quantity
                        num_small_green = barrel.quantity
                    elif barrel.potion_type[2] == 1:
                        barrel_catalog_dict['SMALL_BLUE_BARREL'] = barrel.quantity
                        num_small_blue = barrel.quantity
                case 2500:
                    if barrel.potion_type[0] == 1:
                        barrel_catalog_dict['MEDIUM_RED_BARREL'] = barrel.quantity
                        num_med_red = barrel.quantity
                    elif barrel.potion_type[1] == 1:
                        barrel_catalog_dict['MEDIUM_GREEN_BARREL'] = barrel.quantity
                        num_med_green = barrel.quantity
                    elif barrel.potion_type[2] == 1:
                        barrel_catalog_dict['MEDIUM_BLUE_BARREL'] = barrel.quantity
                        num_med_blue = barrel.quantity
                case 10000:
                    if barrel.potion_type[0] == 1:
                        barrel_catalog_dict['LARGE_RED_BARREL'] = barrel.quantity
                        num_large_red = barrel.quantity
                    elif barrel.potion_type[1] == 1:
                        barrel_catalog_dict['LARGE_GREEN_BARREL'] = barrel.quantity
                        num_large_green = barrel.quantity
                    elif barrel.potion_type[2] == 1:
                        barrel_catalog_dict['LARGE_BLUE_BARREL'] = barrel.quantity
                        num_large_blue = barrel.quantity
        
        red_budget = int((red_ml_needed / total_ml_needed) * gold_available)
        green_budget = int((green_ml_needed / total_ml_needed) * gold_available)
        blue_budget = int((blue_ml_needed / total_ml_needed) * gold_available)

        print(f"red budget: {red_budget}")
        print(f"green budget: {green_budget}")
        print(f"blue budget: {blue_budget}")
        print(barrel_catalog_dict)

        LARGE_ML = 10000
        MEDIUM_ML = 2500
        SMALL_ML = 500
        MINI_ML = 200

        LARGE_ML_COST = 500
        MEDIUM_ML_COST = 250
        SMALL_ML_COST = 100
        MINI_ML_COST = 60

        barrels_purchased = 0
        times_ran = 0
        #Get optimal barrel

        #IMPORTANT
        #need to update barrel quantity or else break if buy too many barrels!!!!
        while (True):
            barrels_purchased = 0
            for ml_needed in ml_priority_list:
                match ml_needed:
                    case 'red':
                        #LARGE RED
                        if red_ml_needed >= LARGE_ML and (total_ml + LARGE_ML) <= ml_capacity and num_large_red > 0 and red_budget >= LARGE_ML_COST:
                            num_to_purchase = get_num_barrel_to_purchase(red_ml_needed, LARGE_ML, ml_capacity, num_large_red, red_budget, LARGE_ML_COST)
                            if num_to_purchase > 0:
                                red_ml_needed -= num_to_purchase * LARGE_ML
                                total_ml += num_to_purchase * LARGE_ML
                                gold_available -= num_to_purchase * LARGE_ML_COST
                                red_budget -= num_to_purchase * LARGE_ML_COST
                                barrels_purchased += num_to_purchase
                                num_large_red -= num_to_purchase
                                barrels_receipt.append({"sku": "LARGE_RED_BARREL", "quantity": num_to_purchase})
                        #MEDIUM RED
                        if red_ml_needed >= MEDIUM_ML and (total_ml + MEDIUM_ML) <= ml_capacity and num_med_red > 0 and red_budget >= MEDIUM_ML_COST:
                            num_to_purchase = get_num_barrel_to_purchase(red_ml_needed, MEDIUM_ML, ml_capacity, num_med_red, gold_available, MEDIUM_ML_COST)
                            if num_to_purchase > 0:
                                red_ml_needed -= num_to_purchase * MEDIUM_ML
                                total_ml += num_to_purchase * MEDIUM_ML
                                gold_available -= num_to_purchase * MEDIUM_ML_COST
                                red_budget -= num_to_purchase * MEDIUM_ML_COST
                                barrels_purchased += num_to_purchase
                                num_med_red -= num_to_purchase
                                barrels_receipt.append({"sku": "MEDIUM_RED_BARREL", "quantity": num_to_purchase})
                        #SMALL RED
                        if red_ml_needed >= SMALL_ML and (total_ml + SMALL_ML) <= ml_capacity and num_small_red > 0 and red_budget >= SMALL_ML_COST:
                            num_to_purchase = get_num_barrel_to_purchase(red_ml_needed, SMALL_ML, ml_capacity, num_small_red, gold_available, SMALL_ML_COST)
                            if num_to_purchase > 0:
                                red_ml_needed -= num_to_purchase * SMALL_ML
                                total_ml += num_to_purchase * SMALL_ML
                                gold_available -= num_to_purchase * SMALL_ML_COST
                                red_budget -= num_to_purchase * SMALL_ML_COST
                                barrels_purchased += num_to_purchase
                                num_small_red -= num_to_purchase
                                barrels_receipt.append({"sku": "SMALL_RED_BARREL", "quantity": num_to_purchase})
                        #MINI RED
                        if red_ml_needed >= MINI_ML and (total_ml + MINI_ML) <= ml_capacity and num_mini_red > 0 and red_budget >= MINI_ML_COST:
                            num_to_purchase = get_num_barrel_to_purchase(red_ml_needed, MINI_ML, ml_capacity, num_mini_red, gold_available, MINI_ML_COST)
                            if num_to_purchase > 0:
                                red_ml_needed -= num_to_purchase * MINI_ML
                                total_ml += num_to_purchase * MINI_ML
                                gold_available -= num_to_purchase * MINI_ML_COST
                                red_budget -= num_to_purchase * MINI_ML_COST
                                barrels_purchased += num_to_purchase
                                num_mini_red -= num_to_purchase
                                barrels_receipt.append({"sku": "MINI_RED_BARREL", "quantity": num_to_purchase})
                    case 'green':
                        #LARGE GREEN
                        if green_ml_needed >= LARGE_ML and (total_ml + LARGE_ML) <= ml_capacity and num_large_green > 0 and green_budget >= LARGE_ML_COST:
                            num_to_purchase = get_num_barrel_to_purchase(green_ml_needed, LARGE_ML, ml_capacity, num_large_green, gold_available, LARGE_ML_COST)
                            if num_to_purchase > 0:
                                green_ml_needed -= num_to_purchase * LARGE_ML
                                total_ml += num_to_purchase * LARGE_ML
                                gold_available -= num_to_purchase * LARGE_ML_COST
                                green_budget -= num_to_purchase * LARGE_ML_COST
                                barrels_purchased += num_to_purchase
                                num_large_green -= num_to_purchase
                                barrels_receipt.append({"sku": "LARGE_GREEN_BARREL", "quantity": num_to_purchase})
                        #MEDIUM GREEN
                        if green_ml_needed >= MEDIUM_ML and (total_ml + MEDIUM_ML) <= ml_capacity and num_med_green > 0 and green_budget >= MEDIUM_ML_COST:
                            num_to_purchase = get_num_barrel_to_purchase(green_ml_needed, MEDIUM_ML, ml_capacity, num_med_green, gold_available, MEDIUM_ML_COST)
                            if num_to_purchase > 0:
                                green_ml_needed -= num_to_purchase * MEDIUM_ML
                                total_ml += num_to_purchase * MEDIUM_ML
                                gold_available -= num_to_purchase * MEDIUM_ML_COST
                                green_budget -= num_to_purchase * MEDIUM_ML_COST
                                barrels_purchased += num_to_purchase
                                barrels_receipt.append({"sku": "MEDIUM_GREEN_BARREL", "quantity": num_to_purchase})
                        #SMALL GREEN
                        if green_ml_needed >= SMALL_ML and (total_ml + SMALL_ML) <= ml_capacity and num_small_green > 0 and green_budget >= SMALL_ML_COST:
                            num_to_purchase = get_num_barrel_to_purchase(green_ml_needed, SMALL_ML, ml_capacity, num_small_green, gold_available, SMALL_ML_COST)
                            if num_to_purchase > 0:
                                green_ml_needed -= num_to_purchase * SMALL_ML
                                total_ml += num_to_purchase * SMALL_ML
                                gold_available -= num_to_purchase * SMALL_ML_COST
                                green_budget -= num_to_purchase * SMALL_ML_COST
                                barrels_purchased += num_to_purchase
                                barrels_receipt.append({"sku": "SMALL_GREEN_BARREL", "quantity": num_to_purchase})
                        #MINI GREEN
                        if green_ml_needed >= MINI_ML and (total_ml + MINI_ML) <= ml_capacity and num_mini_green > 0 and green_budget >= MINI_ML_COST:
                            num_to_purchase = get_num_barrel_to_purchase(green_ml_needed, MINI_ML, ml_capacity, num_mini_green, gold_available, MINI_ML_COST)
                            if num_to_purchase > 0:
                                green_ml_needed -= num_to_purchase * MINI_ML
                                total_ml += num_to_purchase * MINI_ML
                                gold_available -= num_to_purchase * MINI_ML_COST
                                green_budget -= num_to_purchase * MINI_ML_COST
                                barrels_purchased += num_to_purchase
                                barrels_receipt.append({"sku": "MINI_GREEN_BARREL", "quantity": num_to_purchase})
                    case 'blue':
                        #LARGE BLUE
                        if blue_ml_needed >= LARGE_ML and (total_ml + LARGE_ML) <= ml_capacity and num_large_blue > 0 and blue_budget >= (LARGE_ML_COST + 100):
                            num_to_purchase = get_num_barrel_to_purchase(blue_ml_needed, LARGE_ML, ml_capacity, num_large_blue, gold_available, LARGE_ML_COST + 100)
                            if num_to_purchase > 0:
                                blue_ml_needed -= num_to_purchase * LARGE_ML
                                total_ml += num_to_purchase * LARGE_ML
                                gold_available -= num_to_purchase * (LARGE_ML_COST + 100)
                                blue_budget -= num_to_purchase * (LARGE_ML_COST + 100)
                                barrels_purchased += num_to_purchase
                                barrels_receipt.append({"sku": "LARGE_BLUE_BARREL", "quantity": num_to_purchase})
                        #MEDIUM BLUE
                        if blue_ml_needed >= MEDIUM_ML and (total_ml + MEDIUM_ML) <= ml_capacity and num_med_blue > 0 and blue_budget >= (MEDIUM_ML_COST + 50):
                            num_to_purchase = get_num_barrel_to_purchase(blue_ml_needed, MEDIUM_ML, ml_capacity, num_med_blue, gold_available, MEDIUM_ML_COST + 50)
                            if num_to_purchase > 0:
                                blue_ml_needed -= num_to_purchase * MEDIUM_ML
                                total_ml += num_to_purchase * MEDIUM_ML
                                gold_available -= num_to_purchase * (MEDIUM_ML_COST + 50)
                                blue_budget -= num_to_purchase * (MEDIUM_ML_COST + 50)
                                barrels_purchased += num_to_purchase
                                barrels_receipt.append({"sku": "MEDIUM_BLUE_BARREL", "quantity": num_to_purchase})
                        #SMALL BLUE
                        if blue_ml_needed >= SMALL_ML and (total_ml + SMALL_ML) <= ml_capacity and num_small_blue > 0 and blue_budget >= (SMALL_ML_COST + 20):
                            num_to_purchase = get_num_barrel_to_purchase(blue_ml_needed, SMALL_ML, ml_capacity, num_small_blue, gold_available, SMALL_ML_COST + 20)
                            if num_to_purchase > 0:
                                blue_ml_needed -= num_to_purchase * SMALL_ML
                                total_ml += num_to_purchase * SMALL_ML
                                gold_available -= num_to_purchase * (SMALL_ML_COST + 20)
                                blue_budget -= num_to_purchase * (SMALL_ML_COST + 20)
                                barrels_purchased += num_to_purchase
                                barrels_receipt.append({"sku": "SMALL_BLUE_BARREL", "quantity": num_to_purchase})
                        #MINI BLUE
                        if blue_ml_needed >= MINI_ML and (total_ml + MINI_ML) <= ml_capacity and num_mini_blue > 0 and blue_budget >=  MINI_ML_COST:
                            num_to_purchase = get_num_barrel_to_purchase(blue_ml_needed, MINI_ML, ml_capacity, num_mini_blue, gold_available, MINI_ML_COST)
                            if num_to_purchase > 0:
                                blue_ml_needed -= num_to_purchase * MINI_ML
                                total_ml += num_to_purchase * MINI_ML
                                gold_available -= num_to_purchase * MINI_ML_COST
                                blue_budget -= num_to_purchase * MINI_ML_COST
                                barrels_purchased += num_to_purchase
                                barrels_receipt.append({"sku": "MINI_BLUE_BARREL", "quantity": num_to_purchase})
            times_ran += 1
            red_budget = gold_available
            green_budget = gold_available
            blue_budget = gold_available
            
            did_not_buy_on_second_pass = barrels_purchased == 0 and times_ran > 1
            if did_not_buy_on_second_pass:
                break
         
    print(f"BARRELS ORDERED: {barrels_receipt}")
    print(f"Gold spent: {inventory['gold'] - gold_available}")
    print(f"Gold left: {gold_available}")
    return barrels_receipt

def get_num_barrel_to_purchase(ml_needed: int, ml_per_barrel: int, ml_capacity: int, barrel_quantity: int, gold_available: int, price: int):
    num_to_purchase = 0
    #if ml_needed >= LARGE_ML and (total_ml + LARGE_ML) <= ml_capacity and barrel_quantity > 0:
    num_to_purchase = ml_needed // ml_per_barrel
    if num_to_purchase > barrel_quantity:
        num_to_purchase = barrel_quantity
    if (num_to_purchase * price) > gold_available:
        num_to_purchase = gold_available // price
    return int(num_to_purchase)