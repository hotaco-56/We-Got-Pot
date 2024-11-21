import sqlalchemy
from src import database as db
from src.api import info

def get_day_plan():
    with db.engine.begin() as connection:
        #get plan based on day
        bottle_plan_day = info.current_time.day

        # Check if near end of day
        if info.current_time.hour >= 20:
            #Set to next day
            bottle_plan_day = info.days_of_week[(info.days_of_week.index(info.current_time.day) + 1) % len(info.days_of_week)]
            print(f"end of day!!! switchting plan! to {bottle_plan_day}")

        print(f"Bottling with {bottle_plan_day} plan")
        match bottle_plan_day:
            case "Edgeday":
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM edgeday_plan AS plan
                    JOIN potions
                    ON potions.sku = plan.potion_sku
                    ORDER BY max_quantity
                    """
                )).mappings().fetchall()
            case "Bloomday":
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM bloomday_plan AS plan
                    JOIN potions
                    ON potions.sku = plan.potion_sku
                    ORDER BY max_quantity
                    """
                )).mappings().fetchall()
            case "Arcanaday":
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM arcanaday_plan AS plan
                    JOIN potions
                    ON potions.sku = plan.potion_sku
                    ORDER BY max_quantity
                    """
                )).mappings().fetchall()
            case "Hearthday":
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM hearthday_plan AS plan
                    JOIN potions
                    ON potions.sku = plan.potion_sku
                    ORDER BY max_quantity
                    """
                )).mappings().fetchall()
            case "Crownday":
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM crownday_plan AS plan
                    JOIN potions
                    ON potions.sku = plan.potion_sku
                    ORDER BY max_quantity
                    """
                )).mappings().fetchall()
            case "Blesseday":
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM blesseday_plan AS plan
                    JOIN potions
                    ON potions.sku = plan.potion_sku
                    ORDER BY max_quantity
                    """
                )).mappings().fetchall()
            case "Soulday":
                bottle_plan = connection.execute(sqlalchemy.text(
                    """
                    SELECT DISTINCT *
                    FROM soulday_plan AS plan
                    JOIN potions
                    ON potions.sku = plan.potion_sku
                    ORDER BY max_quantity
                    """
                )).mappings().fetchall()
    return bottle_plan