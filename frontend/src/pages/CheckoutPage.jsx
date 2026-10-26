import { useEffect, useState } from "react";
import { api, formatPrice } from "../api.js";
import { ProductImage } from "../components/ProductCard.jsx";
import { navigate } from "../hooks/useHashRoute.js";
import { payWithRazorpay } from "../lib/razorpay.js";

const ADDRESS_KEY = "furniture-store-address";
const EMPTY_ADDRESS = { name: "", phone: "", line1: "", line2: "", city: "", state: "", pincode: "" };

const STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
  "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
  "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
  "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
  "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
  "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
];

// Remember the last address on this device so returning customers don't retype it.
const loadAddress = () => {
  try {
    return { ...EMPTY_ADDRESS, ...JSON.parse(localStorage.getItem(ADDRESS_KEY) || "{}") };
  } catch {
    return EMPTY_ADDRESS;
  }
};
const saveAddress = (address) => {
  try {
    localStorage.setItem(ADDRESS_KEY, JSON.stringify(address));
  } catch {
    /* not essential */
  }
};

// Same rules as the server (models.py Address); checking here gives instant feedback,
// but the server always checks again because browser code can be bypassed.
function validate(a) {
  const phone = a.phone.replace(/\s/g, "").replace(/^\+91/, "");
  if (a.name.trim().length < 2) return "Enter the full name for delivery.";
  if (!/^[6-9]\d{9}$/.test(phone)) return "Enter a 10-digit mobile number.";
  if (!a.line1.trim()) return "Enter the address (house, street).";
  if (!a.city.trim()) return "Enter the city.";
  if (!a.state) return "Choose the state.";
  if (!/^[1-9]\d{5}$/.test(a.pincode.trim())) return "Enter a 6-digit pincode.";
  return "";
}

// Checkout for Buy Now (params.product) or the whole cart.
export default function CheckoutPage({ params, user, cart, onPaid }) {
  const buyNowId = params.product ? Number(params.product) : null;
  const [buyNowProduct, setBuyNowProduct] = useState(null);
  const [address, setAddress] = useState(() => {
    const saved = loadAddress();
    return { ...saved, name: saved.name || user.name };
  });
  const [error, setError] = useState("");
  const [status, setStatus] = useState("idle"); // idle | paying

  useEffect(() => {
    if (buyNowId) api.product(buyNowId).then(setBuyNowProduct).catch((err) => setError(err.message));
  }, [buyNowId]);

  // What is being bought: [{ product, quantity }]
  const items = buyNowId
    ? buyNowProduct ? [{ product: buyNowProduct, quantity: 1 }] : []
    : cart?.items ?? [];
  const total = items.reduce((sum, i) => sum + i.product.price * i.quantity, 0);

  const update = (key) => (e) => {
    setAddress({ ...address, [key]: e.target.value });
    if (error) setError(""); // hide an old error once the user starts fixing it
  };

  const pay = async (e) => {
    e.preventDefault();
    const problem = validate(address);
    if (problem) {
      setError(problem);
      return;
    }
    setError("");
    setStatus("paying");
    saveAddress(address);
    try {
      const source = buyNowId ? { product_id: buyNowId, quantity: 1 } : { cart_id: cart.id };
      const { order, razorpay } = await api.createOrder({ ...source, address });
      const payment = await payWithRazorpay({ razorpay, order, user });
      await api.verifyPayment(order.id, payment); // the server checks the signature
      onPaid();
      navigate(`/orders/${order.id}?paid=1`);
    } catch (err) {
      setError(err.message);
      setStatus("idle");
    }
  };

  if (!buyNowId && cart && cart.items.length === 0) {
    return (
      <main className="narrow">
        <div className="panel center">
          <h2>Your cart is empty</h2>
          <button className="primary" onClick={() => navigate("/")}>Continue shopping</button>
        </div>
      </main>
    );
  }

  return (
    <main className="checkout">
      <form className="panel" onSubmit={pay} aria-label="Delivery address">
        <h2>Delivery address</h2>
        <label>
          Full name
          <input value={address.name} onChange={update("name")} autoComplete="name" />
        </label>
        <label>
          Mobile number
          <input value={address.phone} onChange={update("phone")} inputMode="numeric" autoComplete="tel"
                 placeholder="10-digit number" />
        </label>
        <label>
          Address line 1
          <input value={address.line1} onChange={update("line1")} autoComplete="address-line1"
                 placeholder="House no., street" />
        </label>
        <label>
          <span>Address line 2 <span className="muted">(optional)</span></span>
          <input value={address.line2} onChange={update("line2")} autoComplete="address-line2"
                 placeholder="Area, landmark" />
        </label>
        <div className="row">
          <label>
            City
            <input value={address.city} onChange={update("city")} autoComplete="address-level2" />
          </label>
          <label>
            Pincode
            <input value={address.pincode} onChange={update("pincode")} inputMode="numeric"
                   autoComplete="postal-code" maxLength={6} />
          </label>
        </div>
        <label>
          State
          <select value={address.state} onChange={update("state")}>
            <option value="">Choose…</option>
            {STATES.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>

        {error && <p className="error" role="alert">{error}</p>}

        <button className="primary wide" type="submit" disabled={status === "paying" || items.length === 0}>
          {status === "paying" ? "Processing…" : `Pay ${formatPrice(total)}`}
        </button>
        <p className="muted small center">Payments are processed securely by Razorpay (test mode).</p>
      </form>

      <aside className="panel summary" aria-label="Order summary">
        <h2>Order summary</h2>
        <ul className="summary-items">
          {items.map(({ product, quantity }) => (
            <li key={product.id}>
              <ProductImage product={product} size="sm" />
              <div>
                <p>{product.name}</p>
                <p className="muted">Qty {quantity} × {formatPrice(product.price)}</p>
              </div>
              <strong>{formatPrice(product.price * quantity)}</strong>
            </li>
          ))}
        </ul>
        <div className="cart-total">
          <span>Total</span>
          <strong>{formatPrice(total)}</strong>
        </div>
      </aside>
    </main>
  );
}
