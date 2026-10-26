"""Domain objects: Product, CartItem, Cart, User, Address, OrderItem and Order.

These classes hold the business rules (for example, how a cart total is
calculated or what a valid address looks like) so the HTTP routes and the SQL
code stay simple.
"""

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def to_iso(value):
    """Timestamps come back as text from SQLite and as datetime from PostgreSQL;
    always send them to the frontend as one ISO-8601 UTC string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value).replace(" ", "T") + "Z"


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

    FIELDS = ("id", "name", "category", "style", "material", "color", "price",
              "rating", "review_count", "description")

    @classmethod
    def from_row(cls, row):
        """Build a Product from a database row (a dict); extra keys are ignored."""
        return cls(**{key: row[key] for key in cls.FIELDS})

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


@dataclass(frozen=True)
class User:
    id: int
    name: str
    email: str

    @classmethod
    def from_row(cls, row):
        return cls(id=row["id"], name=row["name"], email=row["email"])

    def to_dict(self):
        return asdict(self)  # note: the password hash is never part of a User object

    EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    MIN_PASSWORD_LENGTH = 8

    @classmethod
    def validate_signup(cls, name, email, password):
        """Return (name, email) cleaned up, or raise ValueError with a readable message."""
        name = (name or "").strip() if isinstance(name, str) else ""
        email = (email or "").strip().lower() if isinstance(email, str) else ""
        if not 2 <= len(name) <= 80:
            raise ValueError("name must be 2 to 80 characters")
        if not cls.EMAIL_PATTERN.match(email) or len(email) > 254:
            raise ValueError("enter a valid email address")
        if not isinstance(password, str) or len(password) < cls.MIN_PASSWORD_LENGTH:
            raise ValueError(f"password must be at least {cls.MIN_PASSWORD_LENGTH} characters")
        if len(password) > 128:
            raise ValueError("password must be at most 128 characters")
        return name, email


@dataclass(frozen=True)
class Address:
    """A shipping address in India."""
    name: str
    phone: str
    line1: str
    line2: str
    city: str
    state: str
    pincode: str

    PHONE_PATTERN = re.compile(r"^[6-9]\d{9}$")    # 10-digit Indian mobile number
    PINCODE_PATTERN = re.compile(r"^[1-9]\d{5}$")  # 6 digits, never starting with 0

    @classmethod
    def from_dict(cls, data):
        """Validate raw input and return an Address, or raise ValueError naming the bad field."""
        if not isinstance(data, dict):
            raise ValueError("address is required")

        def text(key, required=True, max_len=100):
            value = data.get(key, "")
            value = value.strip() if isinstance(value, str) else ""
            if required and not value:
                raise ValueError(f"{key} is required")
            if len(value) > max_len:
                raise ValueError(f"{key} must be at most {max_len} characters")
            return value

        phone = text("phone").replace(" ", "")
        if phone.startswith("+91"):
            phone = phone[3:]
        if not cls.PHONE_PATTERN.match(phone):
            raise ValueError("phone must be a 10-digit Indian mobile number")
        pincode = text("pincode").replace(" ", "")
        if not cls.PINCODE_PATTERN.match(pincode):
            raise ValueError("pincode must be 6 digits")

        return cls(name=text("name", max_len=80), phone=phone, line1=text("line1", max_len=200),
                   line2=text("line2", required=False, max_len=200), city=text("city"),
                   state=text("state"), pincode=pincode)

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class OrderItem:
    product: Product
    quantity: int
    unit_price: int  # the price when the order was placed, even if the product price changes later

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def to_dict(self):
        return {"product": self.product.to_dict(), "quantity": self.quantity,
                "unit_price": self.unit_price, "line_total": self.line_total}


@dataclass
class Order:
    id: str
    user_id: int
    status: str
    amount: int
    address: Address
    items: list
    razorpay_order_id: str = None
    created_at: str = None
    paid_at: str = None

    STATUSES = ("pending", "paid", "failed")

    @property
    def amount_paise(self):
        """Razorpay works in the smallest currency unit: ₹1 = 100 paise."""
        return self.amount * 100

    @staticmethod
    def total(items):
        """Total in rupees for a list of (product, quantity) pairs, using database prices."""
        return sum(product.price * quantity for product, quantity in items)

    def to_dict(self):
        return {"id": self.id, "status": self.status, "amount": self.amount,
                "address": self.address.to_dict(), "items": [i.to_dict() for i in self.items],
                "item_count": sum(i.quantity for i in self.items),
                "created_at": to_iso(self.created_at), "paid_at": to_iso(self.paid_at)}
