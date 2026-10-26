import { useEffect, useState } from "react";
import { formatPrice } from "../api.js";

// Fallback colours, used when no photo is found.
const CATEGORY_COLORS = {
  Sofas: "#7c5c4a", Beds: "#4a6b7c", "Dining Tables": "#8a6d3b", Chairs: "#5c7c4a",
  Wardrobes: "#6b4a7c", Bookshelves: "#7c4a5c", "Coffee Tables": "#4a7c6b",
  Desks: "#3b5a8a", Lamps: "#a07a2c", Rugs: "#8a3b4a",
};

// Photos live in frontend/public/images/. Each product tries, in order:
//   1. its own photo:            /images/products/17.jpg   (17 = product id)
//   2. its category's photo:     /images/sofas.jpg
//   3. a coloured tile with the category's first letter
const photoUrls = (product) => [
  `/images/products/${product.id}.jpg`,
  `/images/${product.category.toLowerCase().replace(/\s+/g, "-")}.jpg`,
];

export function ProductImage({ product, size = "md" }) {
  const [attempt, setAttempt] = useState(0); // which photo we're trying; past the end = tile

  // A new product in the same spot (e.g. clicking a "You may also like" item) starts again at photo 1.
  useEffect(() => setAttempt(0), [product.id]);

  const urls = photoUrls(product);
  return (
    <div
      className={`product-image ${size}`}
      style={{ background: CATEGORY_COLORS[product.category] || "#666" }}
    >
      {attempt < urls.length ? (
        <img
          key={urls[attempt]}
          src={urls[attempt]}
          alt={product.name}
          loading="lazy"
          onError={() => setAttempt((a) => a + 1)}
        />
      ) : (
        <span aria-hidden="true">{product.category[0]}</span>
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
