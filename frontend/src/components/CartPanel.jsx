import { formatPrice } from "../api.js";

export default function CartPanel({ cart, onQuantity, onRemove, onClose, onCheckout }) {
  return (
    <aside className="cart" aria-label="Shopping cart">
      <div className="cart-header">
        <h2>Your cart</h2>
        <button className="close" onClick={onClose} aria-label="Close cart">
          ×
        </button>
      </div>

      {cart.items.length === 0 ? (
        <p className="muted">Your cart is empty.</p>
      ) : (
        <ul className="cart-items">
          {cart.items.map(({ product, quantity, line_total }) => (
            <li key={product.id}>
              <div>
                <p>{product.name}</p>
                <p className="muted">{formatPrice(product.price)} each</p>
              </div>
              <div className="qty">
                <button
                  onClick={() => (quantity > 1 ? onQuantity(product.id, quantity - 1) : onRemove(product.id))}
                  aria-label={`Decrease ${product.name}`}
                >
                  −
                </button>
                <span>{quantity}</span>
                <button
                  onClick={() => onQuantity(product.id, quantity + 1)}
                  disabled={quantity >= 10}
                  aria-label={`Increase ${product.name}`}
                >
                  +
                </button>
              </div>
              <strong>{formatPrice(line_total)}</strong>
            </li>
          ))}
        </ul>
      )}

      <div className="cart-total">
        <span>Subtotal ({cart.item_count} items)</span>
        <strong>{formatPrice(cart.subtotal)}</strong>
      </div>
      <button className="primary checkout-button" onClick={onCheckout} disabled={cart.items.length === 0}>
        Proceed to checkout
      </button>
    </aside>
  );
}
