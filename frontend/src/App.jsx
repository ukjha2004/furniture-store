import { useState } from "react";
import { useAuth } from "./hooks/useAuth.js";
import { useCart } from "./hooks/useCart.js";
import { navigate, useHashRoute } from "./hooks/useHashRoute.js";
import CartPanel from "./components/CartPanel.jsx";
import StorePage from "./pages/StorePage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import CheckoutPage from "./pages/CheckoutPage.jsx";
import { OrderPage, OrdersPage } from "./pages/OrdersPage.jsx";

// The app shell: header, cart panel, and whichever page the URL points to.
export default function App() {
  const route = useHashRoute();
  const auth = useAuth();
  const cart = useCart();
  const [cartOpen, setCartOpen] = useState(false);

  // Pages that need a logged-in user send visitors to #/login, then back here afterwards.
  const requireLogin = (destination) => {
    if (auth.user) navigate(destination);
    else navigate(`/login?next=${encodeURIComponent(destination)}`);
  };

  const addToCart = async (productId) => {
    await cart.add(productId);
    setCartOpen(true);
  };

  let page;
  const needsLogin = route.path === "/checkout" || route.path.startsWith("/orders");
  if (auth.checking && needsLogin) {
    page = <main className="narrow"><p className="muted">Loading…</p></main>;
  } else if (needsLogin && !auth.user) {
    // After logging in, auth.user is set and this same URL re-renders as the real page.
    page = <LoginPage auth={auth} onDone={() => {}} />;
  } else if (route.path === "/login") {
    page = <LoginPage auth={auth} onDone={() => navigate(route.params.next || "/")} />;
  } else if (route.path === "/checkout") {
    page = <CheckoutPage params={route.params} user={auth.user} cart={cart.cart} onPaid={cart.refresh} />;
  } else if (route.path === "/orders") {
    page = <OrdersPage />;
  } else if (route.path.startsWith("/orders/")) {
    page = <OrderPage orderId={route.path.slice("/orders/".length)} justPaid={route.params.paid === "1"} />;
  } else {
    page = <StorePage onAddToCart={addToCart} onBuyNow={(id) => requireLogin(`/checkout?product=${id}`)} />;
  }

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="#/">Furniture Store</a>
        <nav className="nav">
          {auth.user ? (
            <>
              <a href="#/orders">My orders</a>
              <span className="muted hello">Hi, {auth.user.name.split(" ")[0]}</span>
              <button className="link" onClick={() => { auth.logout(); navigate("/"); }}>Log out</button>
            </>
          ) : (
            <a href="#/login">Log in</a>
          )}
          <button className="cart-button" onClick={() => setCartOpen(true)} disabled={!cart.cart}>
            Cart ({cart.cart ? cart.cart.item_count : 0})
          </button>
        </nav>
      </header>

      {cart.error && <p className="error banner">{cart.error}</p>}

      {page}

      {cartOpen && cart.cart && (
        <CartPanel
          cart={cart.cart}
          onQuantity={cart.setQuantity}
          onRemove={cart.remove}
          onClose={() => setCartOpen(false)}
          onCheckout={() => {
            setCartOpen(false);
            requireLogin("/checkout");
          }}
        />
      )}
    </div>
  );
}
