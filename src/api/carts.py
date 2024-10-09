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
    with db.engine.begin() as connection:
        cart_id = connection.execute(sqlalchemy.text(
            f"""
            INSERT INTO carts (customer_name, character_class, level)
            VALUES ('{new_cart.customer_name}', '{new_cart.character_class}', '{new_cart.level}');
            SELECT id
            FROM carts
            """
        )).scalar()

    return {"cart_id":cart_id}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """

    print(f"CART CREATED:\nCART_ID: {cart_id}, ITEM_SKU: {item_sku}, AMOUNT: {cart_item.quantity}")

    with db.engine.begin() as connection:
        cart = connection.execute(sqlalchemy.text(
            f"""
            UPDATE catalog
            SET quantity = quantity - {cart_item.quantity}
            WHERE sku = '{item_sku}';

            INSERT INTO cart_items (cart_id, sku, num_ordered)
            VALUES ('{cart_id}', '{item_sku}', '{cart_item.quantity}');

            SELECT customer_name, character_class, level
            FROM carts
            WHERE id = {cart_id}
            """
        )).mappings().fetchone()

    print(f"Level {cart['level']} {cart['character_class']} {cart['customer_name']} added {cart_item.quantity} {item_sku} to their cart")

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    #need to update gold based on price of potion and quantity
    #cart contains info on customer
    #cart items contains reference to carts and reference to catalog and quantity
    #cleanup cart and cart items
    with db.engine.begin() as connection:
        cart = connection.execute(sqlalchemy.text(
            f"""
            UPDATE global_inventory
            SET gold = gold + (purchase.price * item.num_ordered)
            FROM catalog AS purchase
            JOIN cart_items AS item on item.sku = purchase.sku;

            SELECT sku, level, character_class, customer_name, num_ordered
            FROM carts JOIN cart_items on carts.id = cart_items.cart_id;
            """
        )).fetchone()

        price = connection.execute(sqlalchemy.text(
            f"""
            SELECT price
            FROM catalog
            WHERE sku = '{cart[0]}'
            """
        )).scalar()

        connection.execute(sqlalchemy.text(
            f"""
            DELETE 
            FROM cart_items
            WHERE cart_id = {cart_id};

            DELETE 
            FROM carts
            WHERE id = {cart_id}
            """
        ))

        print(f"Level {cart[1]} {cart[2]} {cart[3]} paid {cart[4] * price} gold with {cart_checkout.payment}")
    
    return { "total_potions_bought": cart[4], "total_gold_paid": cart[4] * price }
    
    
