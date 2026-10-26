"""Database connection handling for SQLite (local/tests) and PostgreSQL (production).

`Database` hides the small differences between the two, so the rest of the app
writes SQL once with `?` placeholders and gets rows back as plain dicts.

Which database is used depends on the DATABASE_URL setting:
  postgresql://user:pass@host/dbname  -> PostgreSQL (e.g. Neon)
  anything else (e.g. store.db)       -> a SQLite file
"""

import sqlite3
from pathlib import Path

from flask import current_app, g

from .seed import generate_products

SCHEMA_DIR = Path(__file__).parent


def is_postgres_url(url):
    return url.startswith(("postgres://", "postgresql://"))


class Database:
    def __init__(self, url):
        if is_postgres_url(url):
            import psycopg2              # imported only when needed, so SQLite users don't need it
            import psycopg2.extras

            self.dialect = "postgres"
            self._conn = psycopg2.connect(url)
            self._cursor_args = {"cursor_factory": psycopg2.extras.RealDictCursor}
            self.IntegrityError = psycopg2.IntegrityError
        else:
            self.dialect = "sqlite"
            self._conn = sqlite3.connect(url)
            self._conn.row_factory = sqlite3.Row            # rows behave like dicts
            self._conn.execute("PRAGMA foreign_keys = ON")  # SQLite needs this to enforce foreign keys
            self._cursor_args = {}
            self.IntegrityError = sqlite3.IntegrityError

    def _prepare(self, sql):
        # The app writes "?" placeholders; PostgreSQL's driver expects "%s".
        return sql.replace("?", "%s") if self.dialect == "postgres" else sql

    def execute(self, sql, params=()):
        """Run one statement and return the cursor (for rowcount)."""
        cursor = self._conn.cursor(**self._cursor_args)
        if self.dialect == "postgres":
            # psycopg2 treats "%" specially only when params are given, so pass None when empty.
            cursor.execute(self._prepare(sql), tuple(params) if params else None)
        else:
            cursor.execute(sql, tuple(params))
        return cursor

    def all(self, sql, params=()):
        """All matching rows as a list of dicts."""
        return [dict(row) for row in self.execute(sql, params).fetchall()]

    def one(self, sql, params=()):
        """The first matching row as a dict, or None."""
        row = self.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def scalar(self, sql, params=()):
        """The first column of the first row, e.g. the number from SELECT COUNT(*)."""
        row = self.one(sql, params)
        return next(iter(row.values())) if row else None

    def execute_many(self, sql, rows):
        self._conn.cursor(**self._cursor_args).executemany(self._prepare(sql), rows)

    def run_script(self, script):
        """Run a file with several statements (the schema)."""
        if self.dialect == "postgres":
            self._conn.cursor().execute(script)
        else:
            self._conn.executescript(script)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_db():
    """Return this request's database connection, opening it on first use."""
    if "db" not in g:
        g.db = Database(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(url, product_count=200):
    """Create tables and seed products if the products table is empty."""
    db = Database(url)
    try:
        db.run_script((SCHEMA_DIR / f"schema_{db.dialect}.sql").read_text())
        if db.scalar("SELECT COUNT(*) FROM products") == 0:
            db.execute_many(
                """INSERT INTO products
                   (name, category, style, material, color, price, rating, review_count, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [(p["name"], p["category"], p["style"], p["material"], p["color"], p["price"],
                  p["rating"], p["review_count"], p["description"])
                 for p in generate_products(product_count)],
            )
        db.commit()
    finally:
        db.close()
