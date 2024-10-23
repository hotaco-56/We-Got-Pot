from fastapi import APIRouter
import sqlalchemy
from src import database as db
from src.api import info

router = APIRouter()

num_green_potions = 0

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    with db.engine.begin() as connection:

        # select what I have most of
        # want to implement inserting into catalog table

        current_day = info.current_time.day.lower()

        current_day_catalog = connection.execute(sqlalchemy.text(
            f"""
            SELECT potions.sku, red, green, blue, dark, potions.quantity, price, name
            FROM {current_day}_plan
            JOIN potions
            ON {current_day}_plan.potion_sku = potions.sku
            WHERE potions.quantity > 0
            UNION
            SELECT sku, red, green, blue, dark, quantity, price, name
            FROM potions
            WHERE quantity > 0
            """
        )).mappings().fetchall()


    catalog_list = []

    for potion in current_day_catalog:
        if potion['quantity'] > 0:
            catalog_list.append(
                {
                    "sku": potion['sku'], 
                    "name": potion['name'],
                    "quantity": potion['quantity'], 
                    "price": potion['price'], 
                    "potion_type":  [potion['red'], potion['green'], potion['blue'], potion['dark']]
                }
            )
            if len(catalog_list) == 6:
                    break
    print(f"CATALOG:")
    for sku in catalog_list:
         print(sku)
    return catalog_list

