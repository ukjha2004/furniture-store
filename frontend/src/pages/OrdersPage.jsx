import { useEffect, useState } from "react";
import { api, formatDate, formatPrice } from "../api.js";
import { ProductImage } from "../components/ProductCard.jsx";
import { navigate } from "../hooks/useHashRoute.js";

const STATUS_LABELS = { paid: "Paid", pending: "Payment pending", failed: "Payment failed" };

export function StatusBadge({ status }) {
  return <span className={`badge ${status}`}>{STATUS_LABELS[status] || status}</span>;
}

// #/orders: the logged-in user's order history.
export function OrdersPage() {
  const [orders, setOrders] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.orders().then(setOrders).catch((err) => setError(err.message));
  }, []);

  return (
    <main className="narrow wide-narrow">
      <h2 className="page-title">My orders</h2>
      {error && <p className="error">{error}</p>}
      {!orders && !error && <p className="muted">Loading…</p>}
      {orders?.length === 0 && (
        <div className="panel center">
          <p>You haven't placed any orders yet.</p>
          <button className="primary" onClick={() => navigate("/")}>Start shopping</button>
        </div>
      )}
      <ul className="order-list">
        {orders?.map((order) => (
          <li key={order.id}>
            <button className="panel order-row" onClick={() => navigate(`/orders/${order.id}`)}>
              <ProductImage product={order.items[0].product} size="sm" />
              <div>
                <p><strong>{order.items[0].product.name}</strong>
                  {order.items.length > 1 && <span className="muted"> + {order.items.length - 1} more</span>}</p>
                <p className="muted">{formatDate(order.created_at)} · #{order.id.slice(0, 8)}</p>
              </div>
              <div className="order-row-end">
                <strong>{formatPrice(order.amount)}</strong>
                <StatusBadge status={order.status} />
              </div>
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}

// #/orders/<id>: one order (also the "thank you" page after paying).
export function OrderPage({ orderId, justPaid }) {
  const [order, setOrder] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.order(orderId).then(setOrder).catch((err) => setError(err.message));
  }, [orderId]);

  if (error) return <main className="narrow"><p className="error">{error}</p></main>;
  if (!order) return <main className="narrow"><p className="muted">Loading…</p></main>;

  const a = order.address;
  return (
    <main className="narrow wide-narrow">
      {justPaid && order.status === "paid" && (
        <div className="panel success" role="status">
          <h2>Payment successful 🎉</h2>
          <p>Thank you! Your order has been placed.</p>
        </div>
      )}
      <div className="panel">
        <div className="order-head">
          <div>
            <h2>Order #{order.id.slice(0, 8)}</h2>
            <p className="muted">Placed {formatDate(order.created_at)}</p>
          </div>
          <StatusBadge status={order.status} />
        </div>

        <ul className="summary-items">
          {order.items.map((item) => (
            <li key={item.product.id}>
              <ProductImage product={item.product} size="sm" />
              <div>
                <p>{item.product.name}</p>
                <p className="muted">Qty {item.quantity} × {formatPrice(item.unit_price)}</p>
              </div>
              <strong>{formatPrice(item.line_total)}</strong>
            </li>
          ))}
        </ul>
        <div className="cart-total">
          <span>Total {order.status === "paid" ? "paid" : ""}</span>
          <strong>{formatPrice(order.amount)}</strong>
        </div>

        <h3 className="section-title">Delivering to</h3>
        <p>
          {a.name} · {a.phone}<br />
          {a.line1}{a.line2 && `, ${a.line2}`}<br />
          {a.city}, {a.state} {a.pincode}
        </p>
      </div>
      <button className="secondary" onClick={() => navigate("/orders")}>← All orders</button>
    </main>
  );
}
