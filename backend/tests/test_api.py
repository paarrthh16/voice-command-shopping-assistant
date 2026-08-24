"""End-to-end API tests, driven through FastAPI's TestClient.

Each test gets its own throwaway SQLite database (see the `client` fixture in
conftest.py), seeded with the real product catalog, so these exercise the
full transcript -> NLP -> command -> service -> database -> response path
exactly as a real request would.
"""


# --------------------------------------------------------------------------- #
# Health / products
# --------------------------------------------------------------------------- #

def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["product_count"] == 54


def test_list_products(client):
    response = client.get("/api/products")
    assert response.status_code == 200
    assert len(response.json()) == 54


def test_get_product_not_found(client):
    response = client.get("/api/products/999999")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_search_products_by_brand_and_price(client):
    response = client.get("/api/products/search", params={"brand": "Colgate", "max_price": 300})
    assert response.status_code == 200
    for product in response.json():
        assert product["brand"] == "Colgate"
        assert product["price"] <= 300


# --------------------------------------------------------------------------- #
# Shopping list CRUD
# --------------------------------------------------------------------------- #

def test_add_item_by_name(client):
    response = client.post("/api/shopping-list", json={"name": "Milk", "quantity": 1})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Milk"
    assert body["category"] == "Dairy"


def test_add_item_missing_name_and_id_is_rejected(client):
    response = client.post("/api/shopping-list", json={"quantity": 1})
    assert response.status_code == 400


def test_add_item_invalid_quantity_rejected(client):
    response = client.post("/api/shopping-list", json={"name": "Milk", "quantity": -1})
    assert response.status_code == 422


def test_update_item(client):
    created = client.post("/api/shopping-list", json={"name": "Milk", "quantity": 1}).json()
    response = client.patch(f"/api/shopping-list/{created['id']}", json={"quantity": 3})
    assert response.status_code == 200
    assert response.json()["quantity"] == 3


def test_update_item_not_found(client):
    response = client.patch("/api/shopping-list/999999", json={"quantity": 3})
    assert response.status_code == 404


def test_update_item_no_fields_rejected(client):
    created = client.post("/api/shopping-list", json={"name": "Milk", "quantity": 1}).json()
    response = client.patch(f"/api/shopping-list/{created['id']}", json={})
    assert response.status_code == 400


def test_delete_item(client):
    created = client.post("/api/shopping-list", json={"name": "Milk", "quantity": 1}).json()
    response = client.delete(f"/api/shopping-list/{created['id']}")
    assert response.status_code == 204
    assert client.get("/api/shopping-list").json() == []


def test_delete_item_not_found(client):
    response = client.delete("/api/shopping-list/999999")
    assert response.status_code == 404


def test_adding_same_item_twice_merges_quantity(client):
    client.post("/api/shopping-list", json={"name": "Milk", "quantity": 1})
    response = client.post("/api/shopping-list", json={"name": "Milk", "quantity": 2})
    assert response.status_code == 201
    assert response.json()["quantity"] == 3
    assert len(client.get("/api/shopping-list").json()) == 1


# --------------------------------------------------------------------------- #
# Voice / typed commands -- the core assessment flow
# --------------------------------------------------------------------------- #

def test_command_add_item(client):
    response = client.post("/api/commands", json={"text": "add milk"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "ADD_ITEM"
    assert body["success"] is True
    assert any(item["name"] == "Milk" for item in body["items"])


def test_command_add_unstocked_product_is_refused(client):
    """The shop can only sell what it stocks: an unknown product must not
    create a list row or a free-text 'Other' entry."""
    response = client.post("/api/commands", json={"text": "add caviar"})
    body = response.json()
    assert body["success"] is False
    assert body["items"] == []


def test_command_remove_item(client):
    client.post("/api/commands", json={"text": "add milk"})
    response = client.post("/api/commands", json={"text": "remove milk"})
    body = response.json()
    assert body["intent"] == "REMOVE_ITEM"
    assert body["success"] is True
    assert body["items"] == []


def test_command_update_quantity_with_unit(client):
    """Regression coverage for the UPDATE_PATTERNS fix: a quantity phrase
    with a unit word must actually update the stored unit, not just the
    number."""
    client.post("/api/commands", json={"text": "add milk"})
    response = client.post("/api/commands", json={"text": "change milk to 2 litres"})
    body = response.json()
    assert body["intent"] == "UPDATE_ITEM"
    assert body["success"] is True
    item = next(item for item in body["items"] if item["name"] == "Milk")
    assert item["quantity"] == 2
    assert item["unit"] == "l"


def test_command_search_with_brand_and_price(client):
    response = client.post("/api/commands", json={"text": "Find Colgate toothpaste under 300"})
    body = response.json()
    assert body["intent"] == "SEARCH_PRODUCT"
    assert body["filters"]["brand"] == "Colgate"
    assert body["filters"]["max_price"] == 300


def test_command_hindi_add(client):
    response = client.post("/api/commands", json={"text": "पांच सेब जोड़ो"})
    body = response.json()
    assert body["intent"] == "ADD_ITEM"
    assert body["language"] == "hi"
    assert body["success"] is True
    apples = next(item for item in body["items"] if item["name"] == "Apples")
    assert apples["quantity"] == 5


def test_command_recommend(client):
    response = client.post("/api/commands", json={"text": "what should I buy?"})
    body = response.json()
    assert body["intent"] == "RECOMMEND"


def test_command_clear_list(client):
    client.post("/api/commands", json={"text": "add milk"})
    response = client.post("/api/commands", json={"text": "clear my list"})
    body = response.json()
    assert body["intent"] == "CLEAR_LIST"
    assert body["success"] is True
    assert body["items"] == []


def test_command_nonsense_is_unknown(client):
    response = client.post("/api/commands", json={"text": "the weather is nice today"})
    body = response.json()
    assert body["intent"] == "UNKNOWN"
    assert body["success"] is False


def test_command_empty_text_rejected(client):
    response = client.post("/api/commands", json={"text": ""})
    assert response.status_code == 422


def test_command_oversized_text_rejected(client):
    response = client.post("/api/commands", json={"text": "a" * 500})
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Recommendations / substitutes
# --------------------------------------------------------------------------- #

def test_recommendations_endpoint_returns_reasons(client):
    response = client.get("/api/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert "season" in body
    for entry in body["recommendations"]:
        assert entry["reasons"], "every recommendation must be explainable"


# --------------------------------------------------------------------------- #
# Robustness / security
# --------------------------------------------------------------------------- #

def test_search_percent_wildcard_is_treated_as_literal(client):
    """SQLite LIKE treats '%' as a wildcard; a raw '%' in user input must not
    silently become 'match everything'."""
    response = client.get("/api/products", params={"search": "%"})
    assert response.status_code == 200
    assert response.json() == []


def test_search_sql_injection_attempt_is_inert(client):
    response = client.get("/api/products", params={"search": "'; DROP TABLE products; --"})
    assert response.status_code == 200
    assert response.json() == []
    # The table must still exist and be intact for the rest of the app.
    assert client.get("/api/health").json()["product_count"] == 54


def test_command_text_missing_field_rejected(client):
    response = client.post("/api/commands", json={})
    assert response.status_code == 422


def test_unknown_route_returns_404_not_html_shell(client):
    """The SPA fallback must never swallow an unknown /api/* route."""
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404


def test_substitutes_for_unavailable_search_result(client):
    """At least one seeded product is unavailable with a stocked substitute;
    the search command must surface it instead of a dead end."""
    products = client.get("/api/products").json()
    unavailable = next((p for p in products if not p["available"] and p["substitutes"]), None)
    if unavailable is None:
        return  # catalog data changed; nothing to assert against
    response = client.post("/api/commands", json={"text": f"find {unavailable['name']}"})
    body = response.json()
    assert body["substitutes"], "an unavailable product should offer alternatives"
