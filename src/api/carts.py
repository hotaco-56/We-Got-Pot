from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    
    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }



class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

class Cart:
    customer: Customer
    item_sku: str
    cart_id: int
    quantity: int
    
#LIST OF CARTS
cart_list = [Cart]

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    print(customers)

    return "OK"

@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    customer_cart = Cart()
    customer_cart.customer = new_cart
    cart_list.append(customer_cart)
    print(f"Cart list: {cart_list}")
    return {"cart_id":cart_list.index(customer_cart)}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    red_potions_ordered = green_potions_ordered = blue_potions_ordered = 0
    cart_list[cart_id].item_sku = item_sku

    print(f"CART CREATED: {cart_id}, ITEM_SKU: {item_sku}, AMOUNT: {cart_item.quantity}")

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

        match item_sku:
            case "RED_POTION_0":
                red_potions_ordered = cart_item.quantity
                if (red_potions_ordered > num_red_potions):
                    red_potions_ordered = num_red_potions
                cart_list[cart_id].quantity = red_potions_ordered
            case "GREEN_POTION_0":
                green_potions_ordered = cart_item.quantity
                if (green_potions_ordered > num_green_potions):
                    green_potions_ordered = num_green_potions
                cart_list[cart_id].quantity = green_potions_ordered
            case "BLUE_POTION_0":
                blue_potions_ordered = cart_item.quantity
                if (blue_potions_ordered > num_blue_potions):
                    blue_potions_ordered = num_blue_potions
                cart_list[cart_id].quantity = blue_potions_ordered

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            f"""
            UPDATE global_inventory
            SET num_red_potions = {num_red_potions - red_potions_ordered},
                num_green_potions = {num_green_potions - green_potions_ordered},
                num_blue_potions = {num_blue_potions - blue_potions_ordered}
            """
        ))

    print(f"Level {cart_list[cart_id].customer.level} {cart_list[cart_id].customer.character_class} {cart_list[cart_id].customer.customer_name} ordered:")
    print(f"{cart_list[cart_id].item_sku}")

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """

    print(cart_checkout.payment)

    red_potion_price = 50
    green_potion_price = 50
    blue_potion_price = 50
    gold_paid = 0

    num_potions_bought = cart_list[cart_id].quantity

    match cart_list[cart_id].item_sku:
        case "RED_POTION_0":
            gold_paid = red_potion_price * num_potions_bought
        case "GREEN_POTION_0":
            gold_paid = green_potion_price * num_potions_bought
        case "BLUE_POTION_0":
            gold_paid = blue_potion_price * num_potions_bought
    
    with db.engine.begin() as connection:
        inventory = connection.execute(sqlalchemy.text(
            """
            SELECT gold
            FROM global_inventory
            """
        ))
        inventory_dict = inventory.mappings().fetchone()
        gold = inventory_dict['gold']

        connection.execute(sqlalchemy.text(
            f"""
            UPDATE global_inventory
            SET gold = {gold + gold_paid}
            """
        ))
    print(f"Level {cart_list[cart_id].customer.level} {cart_list[cart_id].customer.character_class} {cart_list[cart_id].customer.customer_name} paid:")
    print(cart_checkout.payment)
    print(gold_paid)
    cart_list.pop(cart_id)
    
    if (num_potions_bought > 0):
        return {"total_potions_bought": num_potions_bought, "total_gold_paid": gold_paid}
    return {"total_potions_bought":[], "total_gold_paid": []}
