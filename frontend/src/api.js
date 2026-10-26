// All calls to the Flask backend live here, so components never build URLs themselves.

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:5000").replace(/\/$/, "");

// The login token, set by useAuth. When present it is sent with every request.
let authToken = null;
export function setAuthToken(token) {
  authToken = token;
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  const response = await fetch(`${API_URL}/api${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data.error || `Request failed (${response.status})`;
    const error = new Error(message.charAt(0).toUpperCase() + message.slice(1)); // "Incorrect email…"
    error.status = response.status; // lets callers react to 401 (logged out) etc.
    throw error;
  }
  return data;
}

const post = (path, body) => request(path, { method: "POST", body: JSON.stringify(body ?? {}) });

export const api = {
  // Products
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

  // Cart
  createCart: () => post("/carts"),
  getCart: (cartId) => request(`/carts/${cartId}`),
  addToCart: (cartId, productId, quantity = 1) =>
    post(`/carts/${cartId}/items`, { product_id: productId, quantity }),
  updateQuantity: (cartId, productId, quantity) =>
    request(`/carts/${cartId}/items/${productId}`, { method: "PUT", body: JSON.stringify({ quantity }) }),
  removeFromCart: (cartId, productId) =>
    request(`/carts/${cartId}/items/${productId}`, { method: "DELETE" }),

  // Login
  signup: (name, email, password) => post("/auth/signup", { name, email, password }),
  login: (email, password) => post("/auth/login", { email, password }),
  me: () => request("/auth/me"),

  // Orders and payment
  createOrder: (body) => post("/orders", body), // { product_id, quantity } or { cart_id }, plus address
  verifyPayment: (orderId, razorpayResponse) => post(`/orders/${orderId}/verify`, razorpayResponse),
  orders: () => request("/orders"),
  order: (id) => request(`/orders/${id}`),
};

export const formatPrice = (rupees) => `₹${rupees.toLocaleString("en-IN")}`;

export const formatDate = (iso) =>
  iso ? new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "";
