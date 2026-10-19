"""Database connection handling.

Flask keeps one SQLite connection per request in `g` and closes it when the
request ends. `init_db` creates the tables and loads sample data the first time.
"""

import sqlite3
from pathlib import Path

from flask import current_app, g

from .seed import generate_products

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row            # rows behave like dicts: row["price"]
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite needs this to enforce foreign keys
    return conn


def get_db():
    """Return this request's connection, opening it on first use."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path, product_count=200):
    """Create tables and seed products if the products table is empty."""
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text())
        (existing,) = conn.execute("SELECT COUNT(*) FROM products").fetchone()
        if existing == 0:
            conn.executemany(
                """INSERT INTO products
                   (name, category, style, material, color, price, rating, review_count, description)
                   VALUES (:name, :category, :style, :material, :color, :price, :rating,
                           :review_count, :description)""",
                generate_products(product_count),
            )
        conn.commit()
    finally:
        conn.close()
