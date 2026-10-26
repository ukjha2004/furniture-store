import { useEffect, useState } from "react";
import { api, formatPrice } from "../api.js";
import { ProductImage } from "./ProductCard.jsx";

// Product details plus "You may also like" from the recommender endpoint.
export default function ProductModal({ productId, onClose, onOpen, onAdd, onBuyNow }) {
  const [product, setProduct] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false; // ignore late responses if the user opens another product
    setProduct(null);
    setError("");
    Promise.all([api.product(productId), api.similar(productId)])
      .then(([p, s]) => {
        if (!cancelled) {
          setProduct(p);
          setSimilar(s);
        }
      })
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [productId]);

  // Close on Escape.
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <button className="close" onClick={onClose} aria-label="Close">
          ×
        </button>
        {error && <p className="error">{error}</p>}
        {!product && !error && <p className="muted">Loading…</p>}
        {product && (
          <>
            <div className="detail">
              <ProductImage product={product} size="lg" />
              <div>
                <h2>{product.name}</h2>
                <p className="muted">
                  {product.category} · {product.style} · {product.material} · {product.color}
                </p>
                <p className="rating">
                  ★ {product.rating.toFixed(1)} <span className="muted">({product.review_count} reviews)</span>
                </p>
                <p>{product.description}</p>
                <p className="price">{formatPrice(product.price)}</p>
                <div className="actions">
                  <button className="primary" onClick={() => onBuyNow(product.id)}>
                    Buy now
                  </button>
                  <button className="secondary" onClick={() => onAdd(product.id)}>
                    Add to cart
                  </button>
                </div>
              </div>
            </div>
            <h3>You may also like</h3>
            <div className="similar">
              {similar.map((s) => (
                <button key={s.id} className="similar-item" onClick={() => onOpen(s.id)}>
                  <ProductImage product={s} size="sm" />
                  <span>{s.name}</span>
                  <strong>{formatPrice(s.price)}</strong>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
