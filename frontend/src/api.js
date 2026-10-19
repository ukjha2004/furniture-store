// All calls to the Flask backend live here, so components never build URLs themselves.

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:5000").replace(/\/$/, "");

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `Request failed (${response.status})`);
  }
  return data;
}

export const api = {
  categories: () => request("/categories"),

  searchProducts: (filters) => {
    // Drop empty values so the URL only contains filters the user actually set.
    const params = new URLSearchParams(
      Object.entries(filters).filter(([, value]) => value !== "" && value != null)
    );
    return request(`/products?${params}`);
  },

  product: (id) => request(`/products/${id}`),
  similar: (id, k = 4) => request(`/products/${id}/similar?k=${k}`),

  createCart: () => request("/carts", { method: "POST" }),
  getCart: (cartId) => request(`/carts/${cartId}`),
  addToCart: (cartId, productId, quantity = 1) =>
    request(`/carts/${cartId}/items`, {
      method: "POST",
      body: JSON.stringify({ product_id: productId, quantity }),
    }),
  updateQuantity: (cartId, productId, quantity) =>
    request(`/carts/${cartId}/items/${productId}`, {
      method: "PUT",
      body: JSON.stringify({ quantity }),
    }),
  removeFromCart: (cartId, productId) =>
    request(`/carts/${cartId}/items/${productId}`, { method: "DELETE" }),
};

export const formatPrice = (rupees) => `₹${rupees.toLocaleString("en-IN")}`;
