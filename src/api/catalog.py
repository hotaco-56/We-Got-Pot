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
                inventory = connection.execute(sqlalchemy.text(
                        """
                        SELECT num_green_potions,
                               num_red_potions,
                               num_blue_potions
                        FROM global_inventory
                        """
                ))
                inventory_dict = inventory.mappings().fetchone()
                num_green_potions = inventory_dict['num_green_potions']
                num_red_potions = inventory_dict['num_red_potions']
                num_blue_potions = inventory_dict['num_blue_potions']
    
    catalog = []
    
    if num_red_potions > 0:
        catalog.append(
               {
                "sku": "RED_POTION_0",
                "name": "red potion",
                "quantity": num_red_potions,
                "price": 50,
                "potion_type": [100, 0, 0, 0],
               }
        )
    
    if num_green_potions > 0:
        catalog.append(
               {
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": num_green_potions,
                "price": 50,
                "potion_type": [0, 100, 0, 0],
               }
        )
                
    if num_blue_potions > 0:
        catalog.append(
               {
                "sku": "BLUE_POTION_0",
                "name": "blue potion",
                "quantity": num_blue_potions,
                "price": 50,
                "potion_type": [0, 0, 100, 0],
               }
        )
    print(f"CATALOG: {catalog}")
    return catalog

