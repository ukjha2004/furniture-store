-- Database schema for the furniture store.
-- Three tables: products, carts, and the items inside each cart.

CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    category     TEXT    NOT NULL,
    style        TEXT    NOT NULL,
    material     TEXT    NOT NULL,
    color        TEXT    NOT NULL,
    price        INTEGER NOT NULL CHECK (price > 0),          -- in INR
    rating       REAL    NOT NULL CHECK (rating BETWEEN 0 AND 5),
    review_count INTEGER NOT NULL DEFAULT 0,
    description  TEXT    NOT NULL
);

-- Indexes speed up the most common filters and sorts.
CREATE INDEX IF NOT EXISTS idx_products_category ON products (category);
CREATE INDEX IF NOT EXISTS idx_products_price    ON products (price);
CREATE INDEX IF NOT EXISTS idx_products_rating   ON products (rating);

CREATE TABLE IF NOT EXISTS carts (
    id         TEXT PRIMARY KEY,                               -- UUID string
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cart_items (
    cart_id    TEXT    NOT NULL REFERENCES carts (id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products (id),
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (cart_id, product_id)                          -- one row per product per cart
);
