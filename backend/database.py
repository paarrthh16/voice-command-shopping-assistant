"""SQLite access layer.

Uses the Python standard library `sqlite3` only. A fresh connection is opened
per operation: SQLite connections are cheap, and this keeps the app safe when
FastAPI runs synchronous route handlers in its worker thread pool.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "shopping.db"
SEED_PATH = BASE_DIR / "data" / "seed_products.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    category    TEXT    NOT NULL,
    brand       TEXT,
    size        TEXT,
    unit        TEXT,
    price       REAL    NOT NULL DEFAULT 0,
    available   INTEGER NOT NULL DEFAULT 1,
    season      TEXT    NOT NULL DEFAULT 'all',
    on_sale     INTEGER NOT NULL DEFAULT 0,
    substitutes TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS shopping_list_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    name       TEXT    NOT NULL,
    category   TEXT    NOT NULL,
    quantity   REAL    NOT NULL DEFAULT 1,
    unit       TEXT    NOT NULL DEFAULT 'piece',
    completed  INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products (id)
);

CREATE TABLE IF NOT EXISTS purchase_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id   INTEGER,
    name         TEXT    NOT NULL,
    category     TEXT    NOT NULL,
    quantity     REAL    NOT NULL DEFAULT 1,
    unit         TEXT    NOT NULL DEFAULT 'piece',
    purchased_at TEXT    NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products (id)
);
"""


@contextmanager
def get_connection():
    """Yield a SQLite connection with dict-like rows, committing on success."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    """Create the schema if needed and seed the product catalog once."""
    with get_connection() as connection:
        connection.executescript(SCHEMA)
        _seed_products(connection)


def _seed_products(connection):
    """Insert the seed catalog only when the products table is empty."""
    count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count:
        return

    with open(SEED_PATH, encoding="utf-8") as seed_file:
        products = json.load(seed_file)

    connection.executemany(
        """
        INSERT INTO products
            (name, category, brand, size, unit, price, available, season, on_sale, substitutes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                product["name"],
                product["category"],
                product.get("brand", ""),
                product.get("size", ""),
                product.get("unit", "piece"),
                float(product.get("price", 0)),
                1 if product.get("available", True) else 0,
                product.get("season", "all"),
                1 if product.get("on_sale", False) else 0,
                ",".join(product.get("substitutes", [])),
            )
            for product in products
        ],
    )
