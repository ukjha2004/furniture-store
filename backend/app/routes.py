"""REST API endpoints (all under /api)."""

from flask import Blueprint, current_app, jsonify, request

from .db import get_db
from .models import Cart
from .repository import SORT_OPTIONS, CartRepository, ProductRepository, SearchQuery

api = Blueprint("api", __name__, url_prefix="/api")

MAX_PAGE_SIZE = 48


class BadRequest(Exception):
    """Raised for invalid input; turned into a 400 JSON response below."""


@api.errorhandler(BadRequest)
def handle_bad_request(err):
    return jsonify(error=str(err)), 400


def _int_arg(name, default=None, minimum=None, maximum=None):
    """Read an optional integer query parameter, validating its range."""
    raw = request.args.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        raise BadRequest(f"'{name}' must be a whole number")
    if minimum is not None and value < minimum:
        raise BadRequest(f"'{name}' must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise BadRequest(f"'{name}' must be at most {maximum}")
    return value


def _json_quantity(default=None):
    body = request.get_json(silent=True) or {}
    quantity = body.get("quantity", default)
    try:
        return Cart.validate_quantity(quantity)
    except ValueError as err:
        raise BadRequest(str(err))


def _require_cart(cart_id):
    carts = CartRepository(get_db())
    if not carts.exists(cart_id):
        return None, (jsonify(error="cart not found"), 404)
    return carts, None


# ---------- Products ----------

@api.get("/health")
def health():
    return jsonify(status="ok")


@api.get("/categories")
def list_categories():
    return jsonify(ProductRepository(get_db()).categories())


@api.get("/products")
def search_products():
    """Search with optional filters, e.g. /api/products?q=oak sofa&max_price=50000&sort=price_asc"""
    sort = request.args.get("sort", "relevance")
    if sort not in SORT_OPTIONS:
        raise BadRequest(f"'sort' must be one of: {', '.join(SORT_OPTIONS)}")

    query = SearchQuery(
        text=request.args.get("q", "").strip(),
        category=request.args.get("category") or None,
        min_price=_int_arg("min_price", minimum=0),
        max_price=_int_arg("max_price", minimum=0),
        sort=sort,
        page=_int_arg("page", default=1, minimum=1),
        page_size=_int_arg("page_size", default=12, minimum=1, maximum=MAX_PAGE_SIZE),
    )
    if query.min_price is not None and query.max_price is not None and query.min_price > query.max_price:
        raise BadRequest("'min_price' cannot be greater than 'max_price'")

    products, total = ProductRepository(get_db()).search(query)
    return jsonify(
        items=[p.to_dict() for p in products],
        total=total,
        page=query.page,
        page_size=query.page_size,
        total_pages=(total + query.page_size - 1) // query.page_size,
    )


@api.get("/products/<int:product_id>")
def get_product(product_id):
    product = ProductRepository(get_db()).get(product_id)
    if product is None:
        return jsonify(error="product not found"), 404
    return jsonify(product.to_dict())


@api.get("/products/<int:product_id>/similar")
def similar_products(product_id):
    repo = ProductRepository(get_db())
    if repo.get(product_id) is None:
        return jsonify(error="product not found"), 404
    k = _int_arg("k", default=4, minimum=1, maximum=12)
    recommender = current_app.extensions["recommender"]
    return jsonify([p.to_dict() for p in repo.get_many(recommender.similar(product_id, k))])


# ---------- Cart ----------

@api.post("/carts")
def create_cart():
    cart = CartRepository(get_db()).create()
    return jsonify(cart.to_dict()), 201


@api.get("/carts/<cart_id>")
def get_cart(cart_id):
    cart = CartRepository(get_db()).load(cart_id)
    if cart is None:
        return jsonify(error="cart not found"), 404
    return jsonify(cart.to_dict())


@api.post("/carts/<cart_id>/items")
def add_item(cart_id):
    """Add a product to the cart, or increase its quantity if already there."""
    carts, error = _require_cart(cart_id)
    if error:
        return error
    body = request.get_json(silent=True) or {}
    product_id = body.get("product_id")
    if not isinstance(product_id, int) or ProductRepository(get_db()).get(product_id) is None:
        return jsonify(error="product not found"), 404

    added = _json_quantity(default=1)
    new_quantity = carts.current_quantity(cart_id, product_id) + added
    try:
        Cart.validate_quantity(new_quantity)
    except ValueError as err:
        raise BadRequest(str(err))
    carts.set_quantity(cart_id, product_id, new_quantity)
    return jsonify(carts.load(cart_id).to_dict()), 201


@api.put("/carts/<cart_id>/items/<int:product_id>")
def update_item(cart_id, product_id):
    """Set an item's exact quantity."""
    carts, error = _require_cart(cart_id)
    if error:
        return error
    if carts.current_quantity(cart_id, product_id) == 0:
        return jsonify(error="item not in cart"), 404
    carts.set_quantity(cart_id, product_id, _json_quantity())
    return jsonify(carts.load(cart_id).to_dict())


@api.delete("/carts/<cart_id>/items/<int:product_id>")
def remove_item(cart_id, product_id):
    carts, error = _require_cart(cart_id)
    if error:
        return error
    if not carts.remove(cart_id, product_id):
        return jsonify(error="item not in cart"), 404
    return jsonify(carts.load(cart_id).to_dict())
