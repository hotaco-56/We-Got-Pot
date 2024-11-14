from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db
from src.api import info

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

    json = []

    if search_page != "":
        search_page = int(search_page)
    else:
        search_page = 0

    match sort_col:
        case search_sort_options.item_sku:
            order_by = 'sku'
        case search_sort_options.customer_name:
            order_by = 'customer_name'
        case search_sort_options.line_item_total:
            order_by = 'num_ordered'
        case search_sort_options.timestamp:
            order_by = 'created_at'

    with db.engine.begin() as connection:
        total_ordered = connection.execute(sqlalchemy.text(
            """
            SELECT COUNT(id)
            FROM carts
            JOIN cart_items
            ON carts.id = cart_items.cart_id
            WHERE
                customer_name ilike :customer_name
                AND
                sku ilike :potion_sku
            """
        ),
            {
                'customer_name': f'%{customer_name}%',
                'potion_sku': f'%{potion_sku}%'
            }
        ).scalar_one()
        result = connection.execute(sqlalchemy.text(
            f"""
            SELECT
                carts.id,
                cart_items.sku,
                carts.customer_name,
                cart_items.num_ordered,
                cart_items.created_at,
                cart_items.gold
            FROM carts
            JOIN cart_items
            ON carts.id = cart_items.cart_id
            WHERE
                customer_name ilike :customer_name
                AND
                sku ilike :potion_sku
            ORDER BY
                {order_by} {sort_order.value}
            LIMIT 5 OFFSET :search_page 
            """
        ),
            {
                'customer_name': f'%{customer_name}%',
                'potion_sku': f'%{potion_sku}%',
                'search_page': search_page
            }
        )
        for row in result:
            json.append(
                {
                    "line_item_id": row.id,
                    "item_sku": f'{row.num_ordered} {row.sku}',
                    "customer_name": row.customer_name,
                    "line_item_total": row.gold,
                    "timestamp": row.created_at
                }
            )
    if search_page < 5:
        previous = ""
    else:
        previous = search_page - 5

    if search_page + 5 >= total_ordered:
        next = ""
    else:
        next = search_page + 5
     
    return {
        "previous": previous,
        "next": next,
        "results": json
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

    customer_dict = {}

    customer_dict['Fighter'] = 0
    customer_dict['Druid'] = 0
    customer_dict['Wizard'] = 0
    customer_dict['Cleric'] = 0
    customer_dict['Paladin'] = 0
    customer_dict['Ranger'] = 0
    customer_dict['Rogue'] = 0
    customer_dict['Monk'] = 0
    customer_dict['Barbarian'] = 0
    customer_dict['Warlock'] = 0
    customer_dict['Bard'] = 0
    customer_dict['Other'] = 0

    for customer in customers:
        customer_dict[customer.character_class] += 1

    print("customers visited:")
    for Class, count in customer_dict.items():
        if count > 0:
            print(f"{Class}s: {count}")

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
            ORDER BY id DESC
            """
        )).scalar()

    print(f"CART CREATED for level {new_cart.level} {new_cart.character_class} {new_cart.customer_name} CART ID: {cart_id}")
    return {"cart_id":cart_id}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    with db.engine.begin() as connection:
        customer = connection.execute(sqlalchemy.text(
            """
            SELECT character_class AS class, customer_name AS name, level
            FROM carts
            WHERE carts.id = :cart_id
            """
        ),{'cart_id': cart_id}).mappings().fetchone()


    with db.engine.begin() as connection:
        potion_price = connection.execute(sqlalchemy.text(
            """
            SELECT price
            FROM potions
            WHERE sku = :sku
            """
        ), {'sku': item_sku}).scalar()

    transaction = f"Level {customer['level']} {customer['class']} {customer['name']} purchased {cart_item.quantity} {item_sku} for {cart_item.quantity * potion_price}"

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO cart_items (cart_id, sku, num_ordered, gold)
            VALUES (
                :cart_id,
                :sku,
                :num_ordered,
                :gold
            );

            INSERT INTO potion_transactions (sku, transaction, quantity)
            VALUES (
                :sku,
                :transaction,
                :quantity
            );
            """
        ),
            {
                'cart_id': cart_id,
                'sku': item_sku,
                'num_ordered': cart_item.quantity,
                'gold': cart_item.quantity * potion_price,
                'transaction': transaction,
                'quantity': -cart_item.quantity
            }
        )

    print(transaction)

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
            UPDATE potions
            SET quantity = quantity - item.num_ordered
            FROM cart_items AS item
            WHERE item.cart_id = {cart_id} AND item.sku = potions.sku;

            UPDATE cart_items
            SET completed = TRUE,
                day = '{info.current_time.day}',
                hour = {info.current_time.hour}
            WHERE cart_items.cart_id = {cart_id};

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
                potion_quantity = (SELECT SUM(quantity) FROM potion_transactions),
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
                    );

            SELECT sku, level, character_class, customer_name, num_ordered
            FROM carts JOIN cart_items ON cart_items.cart_id = {cart_id}
            WHERE carts.id = {cart_id};
            """
        )).fetchone()

        price = connection.execute(sqlalchemy.text(
            f"""
            SELECT price
            FROM potions
            WHERE sku = '{cart[0]}'
            """
        )).scalar()

        print(f"Level {cart[1]} {cart[2]} {cart[3]} paid {cart[4] * price} gold with {cart_checkout.payment}")
    
    return { "total_potions_bought": cart[4], "total_gold_paid": cart[4] * price }
    
    
