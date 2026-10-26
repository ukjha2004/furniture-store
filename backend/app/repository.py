"""All SQL lives here (the "repository pattern").

Routes call these methods instead of writing SQL themselves. Every query uses
`?` placeholders so user input is never pasted into SQL (prevents SQL injection).
The same SQL runs on SQLite and PostgreSQL; `Database` in db.py adapts it.
"""

import uuid
from dataclasses import dataclass
from typing import Optional

from .models import Address, Cart, CartItem, Order, OrderItem, Product, User

# "Relevance" uses a Bayesian average: a 5.0 with 2 reviews should not beat a
# 4.7 with 600 reviews, so each rating is pulled toward 4.0 as if it had 20
# extra average reviews. Products with many reviews keep their real rating.
BAYESIAN_RATING = "(rating * review_count + 4.0 * 20) / (review_count + 20)"

# Only these sort options are allowed; user input picks a key, never raw SQL.
SORT_OPTIONS = {
    "relevance": f"{BAYESIAN_RATING} DESC, id ASC",
    "price_asc": "price ASC, id ASC",
    "price_desc": "price DESC, id ASC",
    "rating": "rating DESC, review_count DESC, id ASC",
}

SEARCHABLE_COLUMNS = ("name", "description", "material", "color", "style", "category")


@dataclass
class SearchQuery:
    text: str = ""
    category: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    sort: str = "relevance"
    page: int = 1
    page_size: int = 12


class ProductRepository:
    def __init__(self, db):
        self.db = db

    def search(self, query: SearchQuery):
        """Return (products on this page, total matching products)."""
        conditions, params = [], []

        # Every word typed must appear in at least one searchable column (AND across words).
        for word in query.text.lower().split():
            ors = " OR ".join(f"LOWER({col}) LIKE ?" for col in SEARCHABLE_COLUMNS)
            conditions.append(f"({ors})")
            params.extend([f"%{word}%"] * len(SEARCHABLE_COLUMNS))

        if query.category:
            conditions.append("category = ?")
            params.append(query.category)
        if query.min_price is not None:
            conditions.append("price >= ?")
            params.append(query.min_price)
        if query.max_price is not None:
            conditions.append("price <= ?")
            params.append(query.max_price)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        order_by = SORT_OPTIONS[query.sort]
        offset = (query.page - 1) * query.page_size

        total = self.db.scalar(f"SELECT COUNT(*) FROM products {where}", params)
        rows = self.db.all(
            f"SELECT * FROM products {where} ORDER BY {order_by} LIMIT ? OFFSET ?",
            [*params, query.page_size, offset],
        )
        return [Product.from_row(r) for r in rows], total

    def get(self, product_id):
        row = self.db.one("SELECT * FROM products WHERE id = ?", (product_id,))
        return Product.from_row(row) if row else None

    def get_many(self, product_ids):
        """Fetch several products, keeping the order of product_ids."""
        if not product_ids:
            return []
        marks = ",".join("?" * len(product_ids))
        rows = self.db.all(f"SELECT * FROM products WHERE id IN ({marks})", list(product_ids))
        by_id = {r["id"]: Product.from_row(r) for r in rows}
        return [by_id[i] for i in product_ids if i in by_id]

    def all(self):
        return [Product.from_row(r) for r in self.db.all("SELECT * FROM products ORDER BY id")]

    def categories(self):
        """Each category with its product count and price range (uses GROUP BY)."""
        return self.db.all(
            """SELECT category, COUNT(*) AS product_count,
                      MIN(price) AS min_price, MAX(price) AS max_price
               FROM products GROUP BY category ORDER BY category"""
        )


class CartRepository:
    def __init__(self, db):
        self.db = db

    def create(self):
        cart_id = str(uuid.uuid4())
        self.db.execute("INSERT INTO carts (id) VALUES (?)", (cart_id,))
        self.db.commit()
        return Cart(id=cart_id)

    def exists(self, cart_id):
        return self.db.one("SELECT 1 AS found FROM carts WHERE id = ?", (cart_id,)) is not None

    def load(self, cart_id):
        """Return the Cart with its items (JOIN with products), or None."""
        if not self.exists(cart_id):
            return None
        rows = self.db.all(
            """SELECT p.*, ci.quantity
               FROM cart_items ci JOIN products p ON p.id = ci.product_id
               WHERE ci.cart_id = ? ORDER BY p.name""",
            (cart_id,),
        )
        return Cart(id=cart_id, items=[CartItem(Product.from_row(r), r["quantity"]) for r in rows])

    def current_quantity(self, cart_id, product_id):
        row = self.db.one("SELECT quantity FROM cart_items WHERE cart_id = ? AND product_id = ?",
                          (cart_id, product_id))
        return row["quantity"] if row else 0

    def set_quantity(self, cart_id, product_id, quantity):
        """Insert the item, or update its quantity if it is already in the cart (upsert)."""
        self.db.execute(
            """INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (?, ?, ?)
               ON CONFLICT (cart_id, product_id) DO UPDATE SET quantity = excluded.quantity""",
            (cart_id, product_id, quantity),
        )
        self.db.commit()

    def remove(self, cart_id, product_id):
        cur = self.db.execute("DELETE FROM cart_items WHERE cart_id = ? AND product_id = ?",
                              (cart_id, product_id))
        self.db.commit()
        return cur.rowcount > 0

    def clear(self, cart_id):
        """Empty the cart (after a successful purchase). Does not commit."""
        self.db.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart_id,))


class EmailTaken(Exception):
    """Raised when signing up with an email that already has an account."""


class UserRepository:
    def __init__(self, db):
        self.db = db

    def create(self, name, email, password_hash):
        try:
            row = self.db.one(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?) RETURNING id",
                (name, email, password_hash),
            )
            self.db.commit()
        except self.db.IntegrityError:
            # The UNIQUE constraint on email caught a duplicate; this also handles two
            # signups with the same email arriving at the same moment.
            self.db.rollback()
            raise EmailTaken(email)
        return User(id=row["id"], name=name, email=email)

    def get(self, user_id):
        row = self.db.one("SELECT id, name, email FROM users WHERE id = ?", (user_id,))
        return User.from_row(row) if row else None

    def get_with_password_hash(self, email):
        """Return (User, password_hash) for a login attempt, or (None, None)."""
        row = self.db.one("SELECT id, name, email, password_hash FROM users WHERE email = ?",
                          (email,))
        return (User.from_row(row), row["password_hash"]) if row else (None, None)


class OrderRepository:
    def __init__(self, db):
        self.db = db

    def create(self, user_id, items, address: Address, cart_id=None):
        """Save a pending order and its items in one transaction.

        `items` is a list of (Product, quantity); prices come from the Product
        objects (loaded from the database), never from the browser.
        """
        order_id = str(uuid.uuid4())
        amount = Order.total(items)
        a = address
        try:
            self.db.execute(
                """INSERT INTO orders (id, user_id, status, amount, cart_id, ship_name, ship_phone,
                                       ship_line1, ship_line2, ship_city, ship_state, ship_pincode)
                   VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (order_id, user_id, amount, cart_id, a.name, a.phone, a.line1, a.line2,
                 a.city, a.state, a.pincode),
            )
            self.db.execute_many(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                [(order_id, product.id, quantity, product.price) for product, quantity in items],
            )
            self.db.commit()
        except Exception:
            self.db.rollback()  # all or nothing: never an order without its items
            raise
        return self.get_for_user(order_id, user_id)

    def set_razorpay_order_id(self, order_id, razorpay_order_id):
        self.db.execute("UPDATE orders SET razorpay_order_id = ? WHERE id = ?",
                        (razorpay_order_id, order_id))
        self.db.commit()

    def mark_failed(self, order_id):
        self.db.execute("UPDATE orders SET status = 'failed' WHERE id = ? AND status = 'pending'",
                        (order_id,))
        self.db.commit()

    def mark_paid(self, order, razorpay_payment_id):
        """Mark the order paid and empty the cart it came from, in one transaction."""
        try:
            self.db.execute(
                """UPDATE orders SET status = 'paid', razorpay_payment_id = ?, paid_at = CURRENT_TIMESTAMP
                   WHERE id = ? AND status = 'pending'""",
                (razorpay_payment_id, order.id),
            )
            cart_id = self.db.scalar("SELECT cart_id FROM orders WHERE id = ?", (order.id,))
            if cart_id:
                CartRepository(self.db).clear(cart_id)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def get_for_user(self, order_id, user_id):
        """The order if it exists AND belongs to this user, else None (so users can't see others' orders)."""
        row = self.db.one("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id))
        return self._build(row) if row else None

    def list_for_user(self, user_id):
        rows = self.db.all("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC, id",
                           (user_id,))
        return [self._build(r) for r in rows]

    def _build(self, row):
        item_rows = self.db.all(
            """SELECT p.*, oi.quantity AS order_quantity, oi.unit_price
               FROM order_items oi JOIN products p ON p.id = oi.product_id
               WHERE oi.order_id = ? ORDER BY p.name""",
            (row["id"],),
        )
        items = [OrderItem(Product.from_row(r), r["order_quantity"], r["unit_price"]) for r in item_rows]
        address = Address(name=row["ship_name"], phone=row["ship_phone"], line1=row["ship_line1"],
                          line2=row["ship_line2"], city=row["ship_city"], state=row["ship_state"],
                          pincode=row["ship_pincode"])
        return Order(id=row["id"], user_id=row["user_id"], status=row["status"], amount=row["amount"],
                     address=address, items=items, razorpay_order_id=row["razorpay_order_id"],
                     created_at=row["created_at"], paid_at=row["paid_at"])
