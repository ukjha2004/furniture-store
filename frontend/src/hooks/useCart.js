import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";

const STORAGE_KEY = "furniture-store-cart-id";

// localStorage can throw (private browsing, blocked storage), so wrap every access.
function readStoredId() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeId(id) {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    /* the cart still works for this visit */
  }
}

// Custom hook: owns the cart state and every cart action.
export function useCart() {
  const [cart, setCart] = useState(null);
  const [error, setError] = useState("");

  // On first load, reuse the saved cart if the server still has it, otherwise make a new one.
  useEffect(() => {
    let cancelled = false;
    async function load() {
      const savedId = readStoredId();
      try {
        const existing = savedId ? await api.getCart(savedId).catch(() => null) : null;
        const next = existing || (await api.createCart());
        storeId(next.id);
        if (!cancelled) setCart(next);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // Wrap each action so errors are shown instead of crashing the page.
  const run = useCallback(async (action) => {
    setError("");
    try {
      setCart(await action());
    } catch (err) {
      setError(err.message);
    }
  }, []);

  return {
    cart,
    error,
    add: (productId) => run(() => api.addToCart(cart.id, productId)),
    setQuantity: (productId, quantity) => run(() => api.updateQuantity(cart.id, productId, quantity)),
    remove: (productId) => run(() => api.removeFromCart(cart.id, productId)),
  };
}
