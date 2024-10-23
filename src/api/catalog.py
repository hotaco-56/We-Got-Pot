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
        catalog = connection.execute(sqlalchemy.text(
            """
            SELECT DISTINCT *
            FROM potions
            WHERE quantity > 0
            ORDER BY quantity DESC
            LIMIT 6
            """
        )).mappings().fetchall()

    catalog_list = []

    for potion in catalog:
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
    print(f"CATALOG:")
    for sku in catalog_list:
         print(sku)
    return catalog_list

