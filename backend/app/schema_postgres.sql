-- Database schema for PostgreSQL (used in production, e.g. Neon).
-- Same tables as schema_sqlite.sql; only the types differ:
--   INTEGER PRIMARY KEY AUTOINCREMENT  ->  SERIAL PRIMARY KEY
--   REAL                               ->  DOUBLE PRECISION
--   TEXT timestamps                    ->  TIMESTAMPTZ (timestamp with time zone)

CREATE TABLE IF NOT EXISTS products (
    id           SERIAL  PRIMARY KEY,
    name         TEXT    NOT NULL,
    category     TEXT    NOT NULL,
    style        TEXT    NOT NULL,
    material     TEXT    NOT NULL,
    color        TEXT    NOT NULL,
    price        INTEGER NOT NULL CHECK (price > 0),
    rating       DOUBLE PRECISION NOT NULL CHECK (rating BETWEEN 0 AND 5),
    review_count INTEGER NOT NULL DEFAULT 0,
    description  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products (category);
CREATE INDEX IF NOT EXISTS idx_products_price    ON products (price);
CREATE INDEX IF NOT EXISTS idx_products_rating   ON products (rating);

CREATE TABLE IF NOT EXISTS carts (
    id         TEXT        PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cart_items (
    cart_id    TEXT    NOT NULL REFERENCES carts (id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products (id),
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (cart_id, product_id)
);

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL      PRIMARY KEY,
    name          TEXT        NOT NULL,
    email         TEXT        NOT NULL UNIQUE,
    password_hash TEXT        NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id                  TEXT        PRIMARY KEY,
    user_id             INTEGER     NOT NULL REFERENCES users (id),
    status              TEXT        NOT NULL CHECK (status IN ('pending', 'paid', 'failed')),
    amount              INTEGER     NOT NULL CHECK (amount > 0),
    cart_id             TEXT,
    razorpay_order_id   TEXT UNIQUE,
    razorpay_payment_id TEXT,
    ship_name           TEXT        NOT NULL,
    ship_phone          TEXT        NOT NULL,
    ship_line1          TEXT        NOT NULL,
    ship_line2          TEXT        NOT NULL DEFAULT '',
    ship_city           TEXT        NOT NULL,
    ship_state          TEXT        NOT NULL,
    ship_pincode        TEXT        NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    paid_at             TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_orders_user ON orders (user_id);

CREATE TABLE IF NOT EXISTS order_items (
    order_id   TEXT    NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products (id),
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    unit_price INTEGER NOT NULL CHECK (unit_price > 0),
    PRIMARY KEY (order_id, product_id)
);
