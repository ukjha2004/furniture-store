import { useState } from "react";
import { formatPrice } from "../api.js";

// Fallback colours, used when a category has no photo yet.
const CATEGORY_COLORS = {
  Sofas: "#7c5c4a", Beds: "#4a6b7c", "Dining Tables": "#8a6d3b", Chairs: "#5c7c4a",
  Wardrobes: "#6b4a7c", Bookshelves: "#7c4a5c", "Coffee Tables": "#4a7c6b",
  Desks: "#3b5a8a", Lamps: "#a07a2c", Rugs: "#8a3b4a",
};

// "Dining Tables" -> "/images/dining-tables.jpg" (files live in frontend/public/images/)
const imageUrl = (category) => `/images/${category.toLowerCase().replace(/\s+/g, "-")}.jpg`;

export function ProductImage({ product, size = "md" }) {
  const [failed, setFailed] = useState(false); // true if the photo is missing

  return (
    <div
      className={`product-image ${size}`}
      style={{ background: CATEGORY_COLORS[product.category] || "#666" }}
    >
      {failed ? (
        <span aria-hidden="true">{product.category[0]}</span>
      ) : (
        <img
          src={imageUrl(product.category)}
          alt={product.name}
          loading="lazy"
          onError={() => setFailed(true)}
        />
      )}
    </div>
  );
}

export default function ProductCard({ product, onOpen, onAdd }) {
  return (
    <article className="card">
      <button className="card-body" onClick={() => onOpen(product.id)}>
        <ProductImage product={product} />
        <h3>{product.name}</h3>
        <p className="muted">{product.category}</p>
        <p className="rating">
          ★ {product.rating.toFixed(1)} <span className="muted">({product.review_count})</span>
        </p>
      </button>
      <div className="card-footer">
        <strong>{formatPrice(product.price)}</strong>
        <button className="primary" onClick={() => onAdd(product.id)}>
          Add to cart
        </button>
      </div>
    </article>
  );
}
