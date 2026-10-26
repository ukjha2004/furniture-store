// Loads Razorpay's checkout script once and opens the payment popup.

const SCRIPT_URL = "https://checkout.razorpay.com/v1/checkout.js";
let loading = null;

function loadScript() {
  if (window.Razorpay) return Promise.resolve();
  if (!loading) {
    loading = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = SCRIPT_URL;
      script.onload = resolve;
      script.onerror = () => {
        loading = null; // allow a retry
        reject(new Error("Could not load Razorpay. Check your internet connection."));
      };
      document.body.appendChild(script);
    });
  }
  return loading;
}

// Opens checkout and resolves with Razorpay's response
// { razorpay_payment_id, razorpay_order_id, razorpay_signature } when the user pays.
// Rejects with error.cancelled = true if the user closes the popup.
export async function payWithRazorpay({ razorpay, order, user }) {
  await loadScript();
  return new Promise((resolve, reject) => {
    const checkout = new window.Razorpay({
      key: razorpay.key_id,
      order_id: razorpay.order_id,
      amount: razorpay.amount, // in paise
      currency: razorpay.currency,
      name: "Furniture Store",
      description: `Order ${order.id.slice(0, 8)}`,
      prefill: { name: order.address.name, email: user.email, contact: order.address.phone },
      theme: { color: "#7b2d6b" },
      handler: resolve,
      modal: {
        ondismiss: () => {
          const error = new Error("Payment cancelled. You can try again.");
          error.cancelled = true;
          reject(error);
        },
      },
    });
    checkout.on("payment.failed", (response) =>
      reject(new Error(response.error?.description || "Payment failed. Please try again."))
    );
    checkout.open();
  });
}
