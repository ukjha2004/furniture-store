"""Payment gateways.

`PaymentGateway` is an abstract base class. `RazorpayGateway` talks to the real
Razorpay API; the tests use a fake one with the same interface, so payment code
can be tested without the internet or real money.

The Razorpay flow:
1. Our server creates a Razorpay order for the amount (create_order).
2. The browser opens Razorpay's checkout popup with that order id; the user pays.
3. Razorpay gives the browser (payment_id, order_id, signature).
4. Our server checks the signature (verify_signature). Only Razorpay and we know
   the key secret, so a valid signature proves the payment really happened.
   The browser alone can never mark an order as paid.
"""

import hashlib
import hmac
from abc import ABC, abstractmethod

import requests


class PaymentError(Exception):
    """The payment provider could not be reached or rejected the request."""


class PaymentGateway(ABC):
    def __init__(self, key_id, key_secret):
        self.key_id = key_id            # public: the browser needs it to open checkout
        self._key_secret = key_secret   # private: never sent to the browser

    @abstractmethod
    def create_order(self, amount_paise, receipt):
        """Create an order with the provider and return its order id."""

    def verify_signature(self, provider_order_id, payment_id, signature):
        """True if signature == HMAC-SHA256(key_secret, "order_id|payment_id")."""
        if not all(isinstance(v, str) and v for v in (provider_order_id, payment_id, signature)):
            return False
        message = f"{provider_order_id}|{payment_id}".encode()
        expected = hmac.new(self._key_secret.encode(), message, hashlib.sha256).hexdigest()
        # compare_digest takes the same time whether the first or last character differs,
        # so attackers can't guess the signature one character at a time.
        return hmac.compare_digest(expected, signature)


class RazorpayGateway(PaymentGateway):
    ORDERS_URL = "https://api.razorpay.com/v1/orders"

    def __init__(self, key_id, key_secret, timeout=15):
        super().__init__(key_id, key_secret)
        self.timeout = timeout

    def create_order(self, amount_paise, receipt):
        try:
            response = requests.post(
                self.ORDERS_URL,
                auth=(self.key_id, self._key_secret),   # HTTP Basic auth, as Razorpay requires
                json={"amount": amount_paise, "currency": "INR", "receipt": receipt},
                timeout=self.timeout,
            )
        except requests.RequestException as err:
            raise PaymentError(f"could not reach Razorpay: {err}") from err
        if response.status_code != 200:
            raise PaymentError(f"Razorpay returned {response.status_code}: {response.text[:200]}")
        return response.json()["id"]
