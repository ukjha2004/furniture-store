"""Domain objects: Product, CartItem and Cart.

These classes hold the business rules (for example, how a cart total is
calculated) so the HTTP routes and the SQL code stay simple.
"""

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    category: str
    style: str
    material: str
    color: str
    price: int
    rating: float
    review_count: int
    description: str

    @classmethod
    def from_row(cls, row):
        """Build a Product from a sqlite3.Row."""
        return cls(**{key: row[key] for key in row.keys()})

    def search_text(self):
        """Text the recommender compares; category is repeated to weight it more."""
        return " ".join([self.name, self.category, self.category, self.style,
                         self.material, self.color, self.description])

    def to_dict(self):
        return asdict(self)


@dataclass
class CartItem:
    product: Product
    quantity: int

    @property
    def line_total(self):
        return self.product.price * self.quantity

    def to_dict(self):
        return {"product": self.product.to_dict(), "quantity": self.quantity,
                "line_total": self.line_total}


@dataclass
class Cart:
    id: str
    items: list = field(default_factory=list)

    MAX_QUANTITY = 10  # per product, a simple business rule

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items)

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items)

    @classmethod
    def validate_quantity(cls, quantity):
        """Raise ValueError unless quantity is a whole number from 1 to MAX_QUANTITY."""
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("quantity must be a whole number")
        if not 1 <= quantity <= cls.MAX_QUANTITY:
            raise ValueError(f"quantity must be between 1 and {cls.MAX_QUANTITY}")
        return quantity

    def to_dict(self):
        return {"id": self.id, "items": [item.to_dict() for item in self.items],
                "item_count": self.item_count, "subtotal": self.subtotal}
