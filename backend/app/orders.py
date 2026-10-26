"""Checkout: create orders (Buy Now or from the cart), pay with Razorpay, view orders.

Every route here needs a logged-in user (@login_required), and users can only
ever see or pay for their own orders.
"""

from flask import Blueprint, current_app, g, jsonify, request

from .auth import login_required
from .db import get_db
from .errors import ApiError, BadRequest
from .models import Address, Cart
from .payments import PaymentError
from .repository import CartRepository, OrderRepository, ProductRepository

orders = Blueprint("orders", __name__, url_prefix="/api/orders")


def _gateway():
    gateway = current_app.extensions.get("payment_gateway")
    if gateway is None:
        raise ApiError("payments are not configured on this server", 503)
    return gateway


def _items_from_request(body):
    """Return (items, cart_id). items = [(Product, quantity), ...] using database prices."""
    db = get_db()
    if "product_id" in body:  # Buy Now: one product
        product_id = body["product_id"]
        product = ProductRepository(db).get(product_id) if isinstance(product_id, int) else None
        if product is None:
            raise ApiError("product not found", 404)
        try:
            quantity = Cart.validate_quantity(body.get("quantity", 1))
        except ValueError as err:
            raise BadRequest(str(err))
        return [(product, quantity)], None

    cart_id = body.get("cart_id")  # Checkout the whole cart
    cart = CartRepository(db).load(cart_id) if isinstance(cart_id, str) else None
    if cart is None:
        raise BadRequest("send either product_id (Buy Now) or cart_id (checkout the cart)")
    if not cart.items:
        raise BadRequest("your cart is empty")
    return [(item.product, item.quantity) for item in cart.items], cart_id


@orders.post("")
@login_required
def create_order():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise BadRequest("request body must be JSON")
    gateway = _gateway()
    try:
        address = Address.from_dict(body.get("address"))
    except ValueError as err:
        raise BadRequest(str(err))
    items, cart_id = _items_from_request(body)

    repo = OrderRepository(get_db())
    order = repo.create(g.user.id, items, address, cart_id)
    try:
        razorpay_order_id = gateway.create_order(order.amount_paise, receipt=order.id)
    except PaymentError as err:
        current_app.logger.error("Razorpay order failed: %s", err)
        repo.mark_failed(order.id)
        raise ApiError("could not start the payment, please try again", 502)
    repo.set_razorpay_order_id(order.id, razorpay_order_id)

    return jsonify(
        order=order.to_dict(),
        # Everything the browser needs to open Razorpay checkout. The key id is
        # public by design; the key secret never leaves the server.
        razorpay={"key_id": gateway.key_id, "order_id": razorpay_order_id,
                  "amount": order.amount_paise, "currency": "INR"},
    ), 201


@orders.post("/<order_id>/verify")
@login_required
def verify_payment(order_id):
    """Called by the browser after Razorpay checkout succeeds."""
    repo = OrderRepository(get_db())
    order = repo.get_for_user(order_id, g.user.id)
    if order is None:
        raise ApiError("order not found", 404)
    if order.status == "paid":
        return jsonify(order.to_dict())  # safe to call twice (idempotent)
    if order.status != "pending":
        raise BadRequest("this order can no longer be paid")

    body = request.get_json(silent=True) or {}
    razorpay_order_id = body.get("razorpay_order_id")
    payment_id = body.get("razorpay_payment_id")
    signature = body.get("razorpay_signature")

    # The payment must be for THIS order, and the signature must be genuine.
    if razorpay_order_id != order.razorpay_order_id or \
            not _gateway().verify_signature(razorpay_order_id, payment_id, signature):
        raise BadRequest("payment verification failed")

    repo.mark_paid(order, payment_id)
    return jsonify(repo.get_for_user(order_id, g.user.id).to_dict())


@orders.get("")
@login_required
def list_orders():
    return jsonify([o.to_dict() for o in OrderRepository(get_db()).list_for_user(g.user.id)])


@orders.get("/<order_id>")
@login_required
def get_order(order_id):
    order = OrderRepository(get_db()).get_for_user(order_id, g.user.id)
    if order is None:
        raise ApiError("order not found", 404)
    return jsonify(order.to_dict())
