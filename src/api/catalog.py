from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

num_green_potions = 0

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    with db.engine.begin() as connection:
        potion_inventory = connection.execute(sqlalchemy.text(
            """ 
            SELECT sku, 
                   name, 
                   quantity, 
                   price, 
                   red, 
                   green, 
                   blue, 
                   dark
            FROM catalog
            ORDER BY quantity DESC
            LIMIT 6 
            """
        ))
        potion_inventory_dict = potion_inventory.mappings().fetchall()
    
    catalog = []

    for potion in potion_inventory_dict:
        if potion['quantity'] > 0:
                catalog.append(
                {
                    "sku": potion['sku'], 
                    "name": potion['name'],
                    "quantity": potion['quantity'], 
                    "price": potion['price'], 
                    "potion_type":  [potion['red'], potion['green'], potion['blue'], potion['dark']]
                }
                )
    print(f"POTTION INVENTORY: {potion_inventory_dict}")
    print(f"CATALOG: {catalog}")
    return catalog

