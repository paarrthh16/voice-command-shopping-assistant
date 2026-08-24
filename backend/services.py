"""Business logic for the product catalog and the shopping list.

Route handlers in `main.py` stay thin: they validate input with Pydantic, call
one of these functions, and translate `ServiceError` into an HTTP response.
"""

from datetime import datetime, timezone
from typing import List, Optional, Sequence

from database import get_connection
from models import Product, ShoppingListItem, ShoppingListItemCreate, ShoppingListItemUpdate

DEFAULT_CATEGORY = "Other"
DEFAULT_UNIT = "piece"

# Units that measure bulk rather than count. A product sold by weight or volume
# still gets counted in pieces when the user does not say a unit: "add 5 apples"
# means five apples, not five kilograms.
BULK_UNITS = {"kg", "g", "l", "ml"}


def _like_pattern(text: str) -> str:
    """Build a LIKE pattern with the wildcard characters escaped.

    Without this, searching for "%" or "_" would match every product, because
    SQLite reads them as wildcards rather than as literal characters.
    """
    escaped = text.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class ServiceError(Exception):
    """Domain error carrying the HTTP status the API should return."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _row_to_product(row) -> Product:
    return Product(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        brand=row["brand"] or "",
        size=row["size"] or "",
        unit=row["unit"] or DEFAULT_UNIT,
        price=row["price"],
        available=bool(row["available"]),
        season=row["season"],
        on_sale=bool(row["on_sale"]),
        substitutes=[s for s in (row["substitutes"] or "").split(",") if s],
    )


def _row_to_item(row) -> ShoppingListItem:
    return ShoppingListItem(
        id=row["id"],
        product_id=row["product_id"],
        name=row["name"],
        category=row["category"],
        quantity=row["quantity"],
        unit=row["unit"],
        completed=bool(row["completed"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #

def list_products(search: Optional[str] = None, category: Optional[str] = None) -> List[Product]:
    query = "SELECT * FROM products"
    conditions, params = [], []

    if search:
        conditions.append(
            "(name LIKE ? ESCAPE '\\' OR brand LIKE ? ESCAPE '\\' OR category LIKE ? ESCAPE '\\')"
        )
        pattern = _like_pattern(search)
        params += [pattern, pattern, pattern]
    if category:
        conditions.append("category = ?")
        params.append(category)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY category, name"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [_row_to_product(row) for row in rows]


def get_product(product_id: int) -> Product:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        raise ServiceError(f"Product {product_id} not found", status_code=404)
    return _row_to_product(row)


def search_products(
    query: Optional[str] = None,
    brand: Optional[str] = None,
    size: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    limit: int = 20,
) -> List[Product]:
    """Filter the catalog. Every argument is optional and combines with AND.

    Query words are matched individually against name, brand and category, so
    "organic apples" and "colgate toothpaste" both work without word order
    mattering.
    """
    sql = "SELECT * FROM products"
    conditions: List[str] = []
    params: List[object] = []

    for word in (query or "").split():
        conditions.append("(name || ' ' || brand || ' ' || category) LIKE ? ESCAPE '\\'")
        params.append(_like_pattern(word))

    if brand:
        conditions.append("lower(brand) = lower(?)")
        params.append(brand)
    if size:
        conditions.append("lower(replace(size, '  ', ' ')) = lower(?)")
        params.append(size)
    if min_price is not None:
        conditions.append("price >= ?")
        params.append(min_price)
    if max_price is not None:
        conditions.append("price <= ?")
        params.append(max_price)
    if category:
        conditions.append("lower(category) = lower(?)")
        params.append(category)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY available DESC, price ASC LIMIT ?"
    params.append(max(1, min(limit, 50)))

    with get_connection() as connection:
        rows = connection.execute(sql, params).fetchall()
    return [_row_to_product(row) for row in rows]


def brand_names() -> List[str]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT DISTINCT brand FROM products WHERE brand <> '' ORDER BY brand"
        ).fetchall()
    return [row["brand"] for row in rows]


def list_categories() -> List[str]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT DISTINCT category FROM products ORDER BY category"
        ).fetchall()
    return [row["category"] for row in rows]


def _find_product_by_name(connection, name: str):
    """Look up a catalog product by exact name first, then by partial match."""
    row = connection.execute(
        "SELECT * FROM products WHERE lower(name) = lower(?)", (name,)
    ).fetchone()
    if row:
        return row
    return connection.execute(
        "SELECT * FROM products WHERE name LIKE ? ESCAPE '\\' ORDER BY length(name) LIMIT 1",
        (_like_pattern(name),),
    ).fetchone()


# --------------------------------------------------------------------------- #
# Shopping list
# --------------------------------------------------------------------------- #

def get_shopping_list() -> List[ShoppingListItem]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM shopping_list_items ORDER BY completed, category, name"
        ).fetchall()
    return [_row_to_item(row) for row in rows]


def add_item(payload: ShoppingListItemCreate, catalog_only: bool = False) -> ShoppingListItem:
    """Add an item by product id or by name.

    If an identical uncompleted item (same name and unit) is already on the
    list, its quantity is increased instead of creating a duplicate row.

    With `catalog_only` the name must resolve to a catalog product: nothing is
    inserted for an unknown product. Voice and typed commands use this, so a
    request for something the shop does not stock never reaches the list.
    """
    if payload.product_id is None and not (payload.name or "").strip():
        raise ServiceError("Provide either a product_id or an item name")

    with get_connection() as connection:
        product_row = None

        if payload.product_id is not None:
            product_row = connection.execute(
                "SELECT * FROM products WHERE id = ?", (payload.product_id,)
            ).fetchone()
            if product_row is None:
                raise ServiceError(f"Product {payload.product_id} not found", status_code=404)
        elif payload.name:
            product_row = _find_product_by_name(connection, payload.name.strip())

        if product_row is None and catalog_only:
            requested = (payload.name or "").strip()
            raise ServiceError(
                f"{requested.title() or 'That product'} is not available in our shop.",
                status_code=404,
            )

        if product_row is not None:
            name = product_row["name"]
            category = payload.category or product_row["category"]
            unit = payload.unit or product_row["unit"] or DEFAULT_UNIT
            if not payload.unit and unit in BULK_UNITS:
                unit = DEFAULT_UNIT
            product_id = product_row["id"]
        else:
            name = payload.name.strip().title()
            category = payload.category or DEFAULT_CATEGORY
            unit = payload.unit or DEFAULT_UNIT
            product_id = None

        timestamp = _now()
        existing = connection.execute(
            """
            SELECT * FROM shopping_list_items
            WHERE lower(name) = lower(?) AND unit = ? AND completed = 0
            """,
            (name, unit),
        ).fetchone()

        if existing:
            new_quantity = existing["quantity"] + payload.quantity
            connection.execute(
                "UPDATE shopping_list_items SET quantity = ?, updated_at = ? WHERE id = ?",
                (new_quantity, timestamp, existing["id"]),
            )
            item_id = existing["id"]
        else:
            cursor = connection.execute(
                """
                INSERT INTO shopping_list_items
                    (product_id, name, category, quantity, unit, completed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (product_id, name, category, payload.quantity, unit, timestamp, timestamp),
            )
            item_id = cursor.lastrowid

        row = connection.execute(
            "SELECT * FROM shopping_list_items WHERE id = ?", (item_id,)
        ).fetchone()

    return _row_to_item(row)


def update_item(item_id: int, payload: ShoppingListItemUpdate) -> ShoppingListItem:
    fields = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not fields:
        raise ServiceError("Provide at least one field to update: quantity, unit or completed")

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM shopping_list_items WHERE id = ?", (item_id,)
        ).fetchone()
        if row is None:
            raise ServiceError(f"Shopping list item {item_id} not found", status_code=404)

        assignments, params = [], []
        for column, value in fields.items():
            assignments.append(f"{column} = ?")
            params.append(int(value) if column == "completed" else value)

        assignments.append("updated_at = ?")
        params += [_now(), item_id]

        connection.execute(
            f"UPDATE shopping_list_items SET {', '.join(assignments)} WHERE id = ?", params
        )

        # Marking an item completed means it was bought: keep it for later
        # history-based features.
        if fields.get("completed") and not row["completed"]:
            updated = connection.execute(
                "SELECT * FROM shopping_list_items WHERE id = ?", (item_id,)
            ).fetchone()
            _record_purchase(connection, updated)

        row = connection.execute(
            "SELECT * FROM shopping_list_items WHERE id = ?", (item_id,)
        ).fetchone()

    return _row_to_item(row)


def delete_item(item_id: int) -> None:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM shopping_list_items WHERE id = ?", (item_id,))
        if cursor.rowcount == 0:
            raise ServiceError(f"Shopping list item {item_id} not found", status_code=404)


def _record_purchase(connection, item_row) -> None:
    connection.execute(
        """
        INSERT INTO purchase_history (product_id, name, category, quantity, unit, purchased_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            item_row["product_id"],
            item_row["name"],
            item_row["category"],
            item_row["quantity"],
            item_row["unit"],
            _now(),
        ),
    )


def find_item_by_name(name: str) -> Optional[ShoppingListItem]:
    """Return the first uncompleted list item with this exact name."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT * FROM shopping_list_items
            WHERE lower(name) = lower(?)
            ORDER BY completed LIMIT 1
            """,
            (name,),
        ).fetchone()
    return _row_to_item(row) if row else None


def clear_list() -> int:
    """Remove every item from the shopping list and return how many were removed."""
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM shopping_list_items")
        return cursor.rowcount


def product_names() -> List[str]:
    with get_connection() as connection:
        rows = connection.execute("SELECT name FROM products ORDER BY name").fetchall()
    return [row["name"] for row in rows]


def products_by_names(names: Sequence[str]) -> List[Product]:
    """Fetch several products in one query (used for substitute lookups)."""
    unique = [name for name in dict.fromkeys(names) if name]
    if not unique:
        return []
    placeholders = ",".join("?" for _ in unique)
    with get_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM products WHERE lower(name) IN ({placeholders})"
            " ORDER BY available DESC, price ASC",
            [name.lower() for name in unique],
        ).fetchall()
    return [_row_to_product(row) for row in rows]


def get_substitutes(product_id: int) -> List[Product]:
    """Alternatives for a product, taken from the catalog's substitutes field."""
    product = get_product(product_id)
    return products_by_names(product.substitutes)


def purchase_history_summary() -> List[dict]:
    """Aggregate purchase history per product: how often, and how recently.

    Aggregation happens in SQL so the recommendation engine never loops over
    raw history rows.
    """
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT name,
                   MAX(category)     AS category,
                   COUNT(*)          AS purchases,
                   MAX(purchased_at) AS last_purchased
            FROM purchase_history
            GROUP BY lower(name)
            ORDER BY purchases DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def count_products() -> int:
    with get_connection() as connection:
        return connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
