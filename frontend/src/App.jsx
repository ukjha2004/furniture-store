import { useEffect, useState } from "react";
import { api } from "./api.js";
import { useCart } from "./hooks/useCart.js";
import Filters from "./components/Filters.jsx";
import ProductCard from "./components/ProductCard.jsx";
import ProductModal from "./components/ProductModal.jsx";
import CartPanel from "./components/CartPanel.jsx";

const EMPTY_FILTERS = { q: "", category: "", min_price: "", max_price: "", sort: "relevance" };

// Wait until the user stops typing before calling the API (fewer requests).
function useDebounced(value, delayMs = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

export default function App() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState([]);
  const [results, setResults] = useState({ items: [], total: 0, total_pages: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [openProductId, setOpenProductId] = useState(null);
  const [cartOpen, setCartOpen] = useState(false);
  const cart = useCart();

  const debouncedFilters = useDebounced(filters);

  useEffect(() => {
    api.categories().then(setCategories).catch((err) => setError(err.message));
  }, []);

  // Any filter change sends the user back to page 1.
  const changeFilters = (next) => {
    setFilters(next);
    setPage(1);
  };

  // Re-run the search whenever the (debounced) filters or the page change.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .searchProducts({ ...debouncedFilters, page, page_size: 12 })
      .then((data) => {
        if (!cancelled) {
          setResults(data);
          setError("");
        }
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [debouncedFilters, page]);

  const addToCart = async (productId) => {
    await cart.add(productId);
    setCartOpen(true);
  };

  return (
    <div className="app">
      <header className="topbar">
        <h1>Furniture Store</h1>
        <button className="cart-button" onClick={() => setCartOpen(true)} disabled={!cart.cart}>
          Cart ({cart.cart ? cart.cart.item_count : 0})
        </button>
      </header>

      <main>
        <Filters filters={filters} categories={categories} onChange={changeFilters} />

        {(error || cart.error) && <p className="error">{error || cart.error}</p>}

        <p className="muted result-count" aria-live="polite">
          {loading ? "Searching…" : `${results.total} products found`}
        </p>

        <section className="grid">
          {results.items.map((product) => (
            <ProductCard key={product.id} product={product} onOpen={setOpenProductId} onAdd={addToCart} />
          ))}
        </section>

        {!loading && results.total === 0 && (
          <p className="empty">
            No products match. <button onClick={() => changeFilters(EMPTY_FILTERS)}>Clear filters</button>
          </p>
        )}

        {results.total_pages > 1 && (
          <nav className="pagination" aria-label="Pages">
            <button disabled={page === 1} onClick={() => setPage(page - 1)}>
              Previous
            </button>
            <span>
              Page {page} of {results.total_pages}
            </span>
            <button disabled={page === results.total_pages} onClick={() => setPage(page + 1)}>
              Next
            </button>
          </nav>
        )}
      </main>

      {openProductId && (
        <ProductModal
          productId={openProductId}
          onClose={() => setOpenProductId(null)}
          onOpen={setOpenProductId}
          onAdd={addToCart}
        />
      )}

      {cartOpen && cart.cart && (
        <CartPanel
          cart={cart.cart}
          onQuantity={cart.setQuantity}
          onRemove={cart.remove}
          onClose={() => setCartOpen(false)}
        />
      )}
    </div>
  );
}
