"""Tests for the scoring engine (backend/recommendations.py).

`score_products` is a pure function: catalog, history and season are all
passed in, and "now" is injectable, so recency scoring is deterministic
instead of depending on the wall clock.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import recommendations as reco


def make_product(name, category="Dairy", price=50.0, available=True,
                  season="all", on_sale=False):
    return SimpleNamespace(
        name=name, category=category, price=price, available=available,
        season=season, on_sale=on_sale,
    )


def test_frequency_bonus_increases_score():
    products = [make_product("Milk")]
    history = [reco.PurchaseStat(name="Milk", category="Dairy", purchases=3, last_purchased=None)]
    scored = reco.score_products(products, history, season="summer")
    assert len(scored) == 1
    assert scored[0].score > 0
    assert any("purchased" in reason.lower() for reason in scored[0].reasons)


def test_frequency_capped():
    """Purchases beyond FREQUENCY_CAP add nothing further."""
    products = [make_product("Milk")]
    history_low = [reco.PurchaseStat(name="Milk", category="Dairy", purchases=5, last_purchased=None)]
    history_high = [reco.PurchaseStat(name="Milk", category="Dairy", purchases=50, last_purchased=None)]
    scored_low = reco.score_products(products, history_low, season="summer")
    scored_high = reco.score_products(products, history_high, season="summer")
    assert scored_low[0].score == scored_high[0].score


def test_recency_recent_purchase_scores_higher_than_old():
    now = datetime(2026, 6, 15, tzinfo=timezone.utc)
    products = [make_product("Milk"), make_product("Bread")]
    history = [
        reco.PurchaseStat(name="Milk", category="Dairy", purchases=1,
                           last_purchased="2026-06-10T00:00:00+00:00"),  # 5 days ago
        reco.PurchaseStat(name="Bread", category="Dairy", purchases=1,
                           last_purchased="2026-05-20T00:00:00+00:00"),  # 26 days ago
    ]
    scored = reco.score_products(products, history, season="summer", now=now)
    by_name = {entry.product.name: entry.score for entry in scored}
    assert by_name["Milk"] > by_name["Bread"]


def test_seasonal_bonus_applied_when_in_season():
    product = make_product("Mango", season="apr,may")
    scored = reco.score_products([product], [], season="summer")
    assert len(scored) == 1
    assert any("season" in reason.lower() for reason in scored[0].reasons)


def test_seasonal_bonus_not_applied_for_all_season_product():
    """A product marked 'all' is stocked year-round and should not be flagged
    as seasonal -- otherwise every product would look seasonal."""
    product = make_product("Milk", season="all")
    scored = reco.score_products([product], [], season="summer")
    # No history, not on sale, "all" season -> only the availability bonus,
    # which alone does not clear score > 0 with a reason, so it is excluded.
    assert scored == []


def test_sale_bonus_applied():
    product = make_product("Chips", on_sale=True)
    scored = reco.score_products([product], [], season="summer")
    assert len(scored) == 1
    assert "On sale" in scored[0].reasons


def test_unavailable_product_penalised():
    """The unavailable penalty (-3.0) outweighs the sale bonus (+1.5), so an
    unavailable product nets negative and is dropped from the list entirely
    rather than merely ranked lower."""
    available = make_product("Milk", available=True, on_sale=True)
    unavailable = make_product("Bread", available=False, on_sale=True)
    scored = reco.score_products([available, unavailable], [], season="summer")
    by_name = {entry.product.name: entry.score for entry in scored}
    assert "Milk" in by_name
    assert "Bread" not in by_name


def test_unavailable_product_with_strong_history_still_ranks_below_available():
    """With enough other signal to clear zero, an unavailable product is
    still surfaced (e.g. "you're running low, but it's out of stock") -- just
    scored lower than an equally-strong available one."""
    available = make_product("Milk", available=True)
    unavailable = make_product("Bread", available=False)
    history = [
        reco.PurchaseStat(name="Milk", category="Dairy", purchases=5, last_purchased=None),
        reco.PurchaseStat(name="Bread", category="Dairy", purchases=5, last_purchased=None),
    ]
    scored = reco.score_products([available, unavailable], history, season="summer")
    by_name = {entry.product.name: entry.score for entry in scored}
    assert by_name["Milk"] > by_name["Bread"]
    assert any("unavailable" in reason.lower() for reason in
               next(e for e in scored if e.product.name == "Bread").reasons)


def test_items_already_on_list_are_excluded():
    products = [make_product("Milk", on_sale=True)]
    scored = reco.score_products(products, [], season="summer", excluded_names=["Milk"])
    assert scored == []


def test_category_affinity_bonus_for_frequent_category():
    products = [make_product("Cheese", category="Dairy")]
    history = [
        reco.PurchaseStat(name="Milk", category="Dairy", purchases=5, last_purchased=None),
        reco.PurchaseStat(name="Yogurt", category="Dairy", purchases=5, last_purchased=None),
    ]
    scored = reco.score_products(products, history, season="summer")
    assert len(scored) == 1
    assert any("dairy" in reason.lower() for reason in scored[0].reasons)


def test_get_current_season_is_deterministic_for_injected_date():
    from datetime import date
    assert reco.get_current_season(date(2026, 1, 15)) == "winter"
    assert reco.get_current_season(date(2026, 7, 1)) == "monsoon"


def test_is_in_season_all_never_matches():
    assert reco.is_in_season("all", "winter") is False


def test_is_in_season_overlap():
    assert reco.is_in_season("dec,jan,feb", "winter") is True
    assert reco.is_in_season("jun,jul", "winter") is False


def test_scoring_is_stable_sort_order():
    """Equal-score products should sort by price then name, never randomly."""
    a = make_product("Apples", on_sale=True, price=40)
    b = make_product("Bananas", on_sale=True, price=40)
    scored = reco.score_products([b, a], [], season="summer")
    assert [entry.product.name for entry in scored] == ["Apples", "Bananas"]
