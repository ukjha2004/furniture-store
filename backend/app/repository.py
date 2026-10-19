"""All SQL lives here (the "repository pattern").

Routes call these methods instead of writing SQL themselves. Every query uses
`?` placeholders so user input is never pasted into SQL (prevents SQL injection).
"""

import uuid
from dataclasses import dataclass
from typing import Optional

from .models import Cart, CartItem, Product

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
    def __init__(self, conn):
        self.conn = conn

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

        (total,) = self.conn.execute(f"SELECT COUNT(*) FROM products {where}", params).fetchone()
        rows = self.conn.execute(
            f"SELECT * FROM products {where} ORDER BY {order_by} LIMIT ? OFFSET ?",
            [*params, query.page_size, offset],
        ).fetchall()
        return [Product.from_row(r) for r in rows], total

    def get(self, product_id):
        row = self.conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return Product.from_row(row) if row else None

    def get_many(self, product_ids):
        """Fetch several products, keeping the order of product_ids."""
        if not product_ids:
            return []
        marks = ",".join("?" * len(product_ids))
        rows = self.conn.execute(f"SELECT * FROM products WHERE id IN ({marks})",
                                 list(product_ids)).fetchall()
        by_id = {r["id"]: Product.from_row(r) for r in rows}
        return [by_id[i] for i in product_ids if i in by_id]

    def all(self):
        return [Product.from_row(r) for r in self.conn.execute("SELECT * FROM products ORDER BY id")]

    def categories(self):
        """Each category with its product count and price range (uses GROUP BY)."""
        rows = self.conn.execute(
            """SELECT category, COUNT(*) AS product_count,
                      MIN(price) AS min_price, MAX(price) AS max_price
               FROM products GROUP BY category ORDER BY category"""
        ).fetchall()
        return [dict(r) for r in rows]


class CartRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(self):
        cart_id = str(uuid.uuid4())
        self.conn.execute("INSERT INTO carts (id) VALUES (?)", (cart_id,))
        self.conn.commit()
        return Cart(id=cart_id)

    def exists(self, cart_id):
        return self.conn.execute("SELECT 1 FROM carts WHERE id = ?", (cart_id,)).fetchone() is not None

    def load(self, cart_id):
        """Return the Cart with its items (JOIN with products), or None."""
        if not self.exists(cart_id):
            return None
        rows = self.conn.execute(
            """SELECT p.*, ci.quantity
               FROM cart_items ci JOIN products p ON p.id = ci.product_id
               WHERE ci.cart_id = ? ORDER BY p.name""",
            (cart_id,),
        ).fetchall()
        items = [
            CartItem(Product(**{k: r[k] for k in r.keys() if k != "quantity"}), r["quantity"])
            for r in rows
        ]
        return Cart(id=cart_id, items=items)

    def current_quantity(self, cart_id, product_id):
        row = self.conn.execute(
            "SELECT quantity FROM cart_items WHERE cart_id = ? AND product_id = ?",
            (cart_id, product_id)).fetchone()
        return row["quantity"] if row else 0

    def set_quantity(self, cart_id, product_id, quantity):
        """Insert the item, or update its quantity if it is already in the cart (upsert)."""
        self.conn.execute(
            """INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (?, ?, ?)
               ON CONFLICT (cart_id, product_id) DO UPDATE SET quantity = excluded.quantity""",
            (cart_id, product_id, quantity),
        )
        self.conn.commit()

    def remove(self, cart_id, product_id):
        cur = self.conn.execute("DELETE FROM cart_items WHERE cart_id = ? AND product_id = ?",
                                (cart_id, product_id))
        self.conn.commit()
        return cur.rowcount > 0
