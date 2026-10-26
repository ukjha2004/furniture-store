"""Checkout and payment tests (using the fake gateway, so no real money or internet)."""

from .base import ApiTestCase
from .fakes import FakeGateway

ADDRESS = {"name": "Asha Kumari", "phone": "9876543210", "line1": "12 MG Road",
           "line2": "Near City Mall", "city": "Dhanbad", "state": "Jharkhand", "pincode": "826001"}


class CheckoutTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.token = self.signup()
        self.headers = self.auth(self.token)

    def buy_now(self, product_id=1, quantity=1, address=ADDRESS, headers=None):
        return self.client.post("/api/orders", headers=headers or self.headers,
                                json={"product_id": product_id, "quantity": quantity, "address": address})

    def pay(self, created, payment_id="pay_fake_1", signature=None, headers=None):
        rz = created["razorpay"]
        return self.client.post(
            f"/api/orders/{created['order']['id']}/verify", headers=headers or self.headers,
            json={"razorpay_order_id": rz["order_id"], "razorpay_payment_id": payment_id,
                  "razorpay_signature": signature or FakeGateway.sign(rz["order_id"], payment_id)})


class CreateOrderTests(CheckoutTestCase):
    def test_buy_now_creates_pending_order_with_server_price(self):
        price = self.client.get("/api/products/1").json["price"]
        response = self.buy_now(product_id=1, quantity=2)
        self.assertEqual(response.status_code, 201, response.json)
        order, rz = response.json["order"], response.json["razorpay"]
        self.assertEqual(order["status"], "pending")
        self.assertEqual(order["amount"], 2 * price)
        self.assertEqual(rz["amount"], 2 * price * 100)          # paise
        self.assertEqual(rz["key_id"], "rzp_test_fake_key")
        self.assertNotIn("secret", str(response.json).lower())   # secret never leaves the server
        self.assertEqual(order["address"]["city"], "Dhanbad")
        self.assertEqual(self.gateway.created, [(2 * price * 100, order["id"])])

    def test_client_cannot_choose_the_price(self):
        body = {"product_id": 1, "quantity": 1, "address": ADDRESS, "amount": 1, "price": 1}
        response = self.client.post("/api/orders", headers=self.headers, json=body)
        real_price = self.client.get("/api/products/1").json["price"]
        self.assertEqual(response.json["order"]["amount"], real_price)

    def test_checkout_from_cart(self):
        cart_id = self.client.post("/api/carts").json["id"]
        self.client.post(f"/api/carts/{cart_id}/items", json={"product_id": 1, "quantity": 2})
        self.client.post(f"/api/carts/{cart_id}/items", json={"product_id": 2})
        subtotal = self.client.get(f"/api/carts/{cart_id}").json["subtotal"]

        response = self.client.post("/api/orders", headers=self.headers,
                                    json={"cart_id": cart_id, "address": ADDRESS})
        self.assertEqual(response.status_code, 201, response.json)
        self.assertEqual(response.json["order"]["amount"], subtotal)
        self.assertEqual(response.json["order"]["item_count"], 3)

    def test_empty_cart_and_bad_inputs(self):
        cart_id = self.client.post("/api/carts").json["id"]
        empty = self.client.post("/api/orders", headers=self.headers,
                                 json={"cart_id": cart_id, "address": ADDRESS})
        self.assertEqual(empty.status_code, 400)
        self.assertEqual(self.buy_now(product_id=99999).status_code, 404)
        self.assertEqual(self.buy_now(quantity=0).status_code, 400)
        self.assertEqual(self.buy_now(quantity=11).status_code, 400)
        self.assertEqual(self.client.post("/api/orders", headers=self.headers,
                                          json={"address": ADDRESS}).status_code, 400)

    def test_address_validation(self):
        bad_addresses = [
            {**ADDRESS, "phone": "12345"},
            {**ADDRESS, "phone": "5876543210"},       # Indian mobiles start with 6-9
            {**ADDRESS, "pincode": "82600"},
            {**ADDRESS, "pincode": "026001"},
            {**ADDRESS, "line1": "   "},
            {k: v for k, v in ADDRESS.items() if k != "city"},
            None,
        ]
        for address in bad_addresses:
            response = self.buy_now(address=address)
            self.assertEqual(response.status_code, 400, address)

    def test_phone_with_country_code_is_accepted(self):
        response = self.buy_now(address={**ADDRESS, "phone": "+91 98765 43210", "line2": ""})
        self.assertEqual(response.status_code, 201, response.json)
        self.assertEqual(response.json["order"]["address"]["phone"], "9876543210")

    def test_login_required(self):
        response = self.client.post("/api/orders", json={"product_id": 1, "address": ADDRESS})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get("/api/orders").status_code, 401)

    def test_gateway_outage_marks_order_failed(self):
        self.gateway.fail_next = True
        response = self.buy_now()
        self.assertEqual(response.status_code, 502)
        orders = self.client.get("/api/orders", headers=self.headers).json
        self.assertEqual([o["status"] for o in orders], ["failed"])


class PaymentTests(CheckoutTestCase):
    def test_valid_signature_marks_order_paid(self):
        created = self.buy_now().json
        response = self.pay(created)
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(response.json["status"], "paid")
        self.assertIsNotNone(response.json["paid_at"])

    def test_forged_signature_is_rejected(self):
        created = self.buy_now().json
        response = self.pay(created, signature="0" * 64)
        self.assertEqual(response.status_code, 400)
        order = self.client.get(f"/api/orders/{created['order']['id']}", headers=self.headers).json
        self.assertEqual(order["status"], "pending")

    def test_signature_for_a_different_order_is_rejected(self):
        first, second = self.buy_now().json, self.buy_now(product_id=2).json
        # Pay for the cheap order, then try to reuse that proof for the other one.
        rz = first["razorpay"]
        response = self.client.post(
            f"/api/orders/{second['order']['id']}/verify", headers=self.headers,
            json={"razorpay_order_id": rz["order_id"], "razorpay_payment_id": "pay_x",
                  "razorpay_signature": FakeGateway.sign(rz["order_id"], "pay_x")})
        self.assertEqual(response.status_code, 400)

    def test_verify_is_idempotent(self):
        created = self.buy_now().json
        self.assertEqual(self.pay(created).status_code, 200)
        again = self.pay(created)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json["status"], "paid")

    def test_paying_from_cart_empties_the_cart(self):
        cart_id = self.client.post("/api/carts").json["id"]
        self.client.post(f"/api/carts/{cart_id}/items", json={"product_id": 3})
        created = self.client.post("/api/orders", headers=self.headers,
                                   json={"cart_id": cart_id, "address": ADDRESS}).json
        # Unpaid: the cart still has the item.
        self.assertEqual(self.client.get(f"/api/carts/{cart_id}").json["item_count"], 1)
        self.pay(created)
        self.assertEqual(self.client.get(f"/api/carts/{cart_id}").json["items"], [])

    def test_order_keeps_price_paid(self):
        created = self.buy_now(product_id=4).json
        self.pay(created)
        order = self.client.get(f"/api/orders/{created['order']['id']}", headers=self.headers).json
        item = order["items"][0]
        self.assertEqual(item["unit_price"] * item["quantity"], order["amount"])


class OrderPrivacyTests(CheckoutTestCase):
    def test_users_cannot_see_or_pay_others_orders(self):
        created = self.buy_now().json
        order_id = created["order"]["id"]
        other = self.auth(self.signup(email="ravi@example.com", name="Ravi"))

        self.assertEqual(self.client.get(f"/api/orders/{order_id}", headers=other).status_code, 404)
        self.assertEqual(self.pay(created, headers=other).status_code, 404)
        self.assertEqual(self.client.get("/api/orders", headers=other).json, [])

    def test_order_history_newest_first(self):
        first = self.buy_now(product_id=1).json["order"]["id"]
        second = self.buy_now(product_id=2).json["order"]["id"]
        ids = [o["id"] for o in self.client.get("/api/orders", headers=self.headers).json]
        self.assertEqual(ids, [second, first])


class NotConfiguredTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.app.extensions["payment_gateway"] = None
        self.headers = self.auth(self.signup())

    def test_checkout_without_razorpay_keys_returns_503(self):
        response = self.client.post("/api/orders", headers=self.headers,
                                    json={"product_id": 1, "address": ADDRESS})
        self.assertEqual(response.status_code, 503)
