"""A fake payment gateway for tests: same interface as RazorpayGateway, no internet."""

import hashlib
import hmac

from app.payments import PaymentError, PaymentGateway


class FakeGateway(PaymentGateway):
    SECRET = "fake_test_secret"

    def __init__(self):
        super().__init__("rzp_test_fake_key", self.SECRET)
        self.created = []        # (amount_paise, receipt) for each order the app created
        self.fail_next = False   # set True to simulate Razorpay being down

    def create_order(self, amount_paise, receipt):
        if self.fail_next:
            self.fail_next = False
            raise PaymentError("simulated outage")
        self.created.append((amount_paise, receipt))
        return f"order_fake_{len(self.created)}"

    @classmethod
    def sign(cls, razorpay_order_id, payment_id):
        """What Razorpay would send the browser after a successful payment."""
        message = f"{razorpay_order_id}|{payment_id}".encode()
        return hmac.new(cls.SECRET.encode(), message, hashlib.sha256).hexdigest()
