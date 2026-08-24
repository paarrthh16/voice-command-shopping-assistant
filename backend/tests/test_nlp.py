"""Tests for the rule-based command parser (backend/nlp.py).

`parse_command` is a pure function, so these tests need no database and no
running server -- they check the intent/entity extraction logic in isolation.
"""

import nlp


# --------------------------------------------------------------------------- #
# ADD_ITEM -- varied phrasings the assessment explicitly calls for
# --------------------------------------------------------------------------- #

def test_add_bare_item():
    result = nlp.parse_command("add milk")
    assert result.intent == nlp.INTENT_ADD
    assert result.item == "milk"
    assert result.quantity is None


def test_add_i_need_phrasing():
    result = nlp.parse_command("I need apples")
    assert result.intent == nlp.INTENT_ADD
    assert result.item == "apples"


def test_add_i_want_to_buy_phrasing():
    result = nlp.parse_command("I want to buy bananas")
    assert result.intent == nlp.INTENT_ADD
    assert result.item == "bananas"


def test_add_to_my_list_phrasing():
    result = nlp.parse_command("Add bananas to my list")
    assert result.intent == nlp.INTENT_ADD
    assert result.item == "bananas"


def test_add_with_please():
    result = nlp.parse_command("please add milk")
    assert result.intent == nlp.INTENT_ADD
    assert result.item == "milk"


def test_add_can_you_phrasing():
    """Regression test: a polite wrapper ("Can you add milk?") used to fall
    through every ADD_PATTERNS entry and read as UNKNOWN."""
    result = nlp.parse_command("Can you add milk?")
    assert result.intent == nlp.INTENT_ADD
    assert result.item == "milk"


def test_remove_could_you_phrasing():
    result = nlp.parse_command("Could you remove milk?")
    assert result.intent == nlp.INTENT_REMOVE
    assert result.item == "milk"


def test_add_quantity_and_unit():
    result = nlp.parse_command("Add 2 bottles of water")
    assert result.intent == nlp.INTENT_ADD
    assert result.item == "water"
    assert result.quantity == 2.0
    assert result.unit == "bottle"


def test_add_word_quantity():
    result = nlp.parse_command("add two litres of milk")
    assert result.intent == nlp.INTENT_ADD
    assert result.item == "milk"
    assert result.quantity == 2.0
    assert result.unit == "l"


def test_buy_phrasing_with_quantity():
    result = nlp.parse_command("Buy 5 oranges")
    assert result.intent == nlp.INTENT_ADD
    assert result.item == "oranges"
    assert result.quantity == 5.0


def test_put_on_list_phrasing():
    result = nlp.parse_command("put milk on my list")
    assert result.intent == nlp.INTENT_ADD
    assert result.item == "milk"


# --------------------------------------------------------------------------- #
# REMOVE_ITEM
# --------------------------------------------------------------------------- #

def test_remove_bare():
    result = nlp.parse_command("Remove milk from my list")
    assert result.intent == nlp.INTENT_REMOVE
    assert result.item == "milk"


def test_delete_phrasing():
    result = nlp.parse_command("delete milk")
    assert result.intent == nlp.INTENT_REMOVE
    assert result.item == "milk"


def test_take_off_list_phrasing():
    result = nlp.parse_command("take milk off my list")
    assert result.intent == nlp.INTENT_REMOVE
    assert result.item == "milk"


def test_dont_need_anymore_phrasing():
    """Regression test: 'anymore' used to be swallowed into the item name
    ("milk anymore"), which stopped this command from matching a real list
    entry named just "Milk"."""
    result = nlp.parse_command("I don't need milk anymore")
    assert result.intent == nlp.INTENT_REMOVE
    assert result.item == "milk"


# --------------------------------------------------------------------------- #
# UPDATE_ITEM
# --------------------------------------------------------------------------- #

def test_update_set_quantity_to():
    result = nlp.parse_command("set milk quantity to 3")
    assert result.intent == nlp.INTENT_UPDATE
    assert result.item == "milk"
    assert result.quantity == 3.0


def test_update_make_quantity():
    result = nlp.parse_command("make the milk quantity 3")
    assert result.intent == nlp.INTENT_UPDATE
    assert result.item == "milk"
    assert result.quantity == 3.0


def test_update_change_to_with_unit():
    """Regression test: a quantity phrase with a unit word ("2 litres") used
    to fail the UPDATE_PATTERNS end anchor entirely and fall through to
    UNKNOWN, so "change milk to 2 litres" silently did nothing."""
    result = nlp.parse_command("change milk to 2 litres")
    assert result.intent == nlp.INTENT_UPDATE
    assert result.item == "milk"
    assert result.quantity == 2.0
    assert result.unit == "l"


def test_update_update_to_with_unit():
    result = nlp.parse_command("update milk to 2 bottles")
    assert result.intent == nlp.INTENT_UPDATE
    assert result.item == "milk"
    assert result.quantity == 2.0
    assert result.unit == "bottle"


def test_update_bare_quantity_no_connector():
    """Regression test: "make water 3 bottles" has no "to" and no
    "quantity" keyword, so it used to fail every UPDATE_PATTERNS entry and
    read as UNKNOWN."""
    result = nlp.parse_command("Make water 3 bottles")
    assert result.intent == nlp.INTENT_UPDATE
    assert result.item == "water"
    assert result.quantity == 3.0
    assert result.unit == "bottle"


# --------------------------------------------------------------------------- #
# SHOW / CLEAR / RECOMMEND
# --------------------------------------------------------------------------- #

def test_show_list():
    result = nlp.parse_command("show my shopping list")
    assert result.intent == nlp.INTENT_SHOW


def test_clear_list():
    result = nlp.parse_command("clear my list")
    assert result.intent == nlp.INTENT_CLEAR


def test_recommend_what_should_i_buy():
    result = nlp.parse_command("what should I buy?")
    assert result.intent == nlp.INTENT_RECOMMEND


# --------------------------------------------------------------------------- #
# SEARCH_PRODUCT -- brand / size / price filters
# --------------------------------------------------------------------------- #

def test_search_under_price():
    result = nlp.parse_command("Find toothpaste under 300")
    assert result.intent == nlp.INTENT_SEARCH
    assert result.filters.max_price == 300.0
    assert "toothpaste" in result.filters.query


def test_search_price_range():
    result = nlp.parse_command("find toothpaste between 200 and 500")
    assert result.intent == nlp.INTENT_SEARCH
    assert result.filters.min_price == 200.0
    assert result.filters.max_price == 500.0


def test_search_size():
    result = nlp.parse_command("find 100g toothpaste")
    assert result.intent == nlp.INTENT_SEARCH
    assert result.filters.size == "100 g"


def test_search_show_me_phrasing():
    result = nlp.parse_command("show me organic apples")
    assert result.intent == nlp.INTENT_SEARCH
    assert "apple" in result.filters.query


def test_extract_brand_splits_known_brand():
    brand, remainder = nlp.extract_brand("colgate toothpaste", ["Colgate", "Amul"])
    assert brand == "Colgate"
    assert remainder == "toothpaste"


def test_extract_brand_none_when_no_match():
    brand, remainder = nlp.extract_brand("toothpaste", ["Colgate"])
    assert brand is None
    assert remainder == "toothpaste"


# --------------------------------------------------------------------------- #
# Entity extraction edge cases
# --------------------------------------------------------------------------- #

def test_extract_entities_dozen_alone_is_unit_not_item():
    entities = nlp.extract_entities("dozen eggs")
    assert entities["quantity"] == 12.0
    assert entities["item"] == "eggs"


def test_extract_entities_trailing_quantity():
    entities = nlp.extract_entities("apples 5")
    assert entities["quantity"] == 5.0
    assert entities["item"] == "apples"


def test_extract_entities_plain_item_no_quantity():
    entities = nlp.extract_entities("milk")
    assert entities["item"] == "milk"
    assert entities["quantity"] is None
    assert entities["unit"] is None


# --------------------------------------------------------------------------- #
# Malformed / nonsense input
# --------------------------------------------------------------------------- #

def test_empty_string_is_unknown():
    result = nlp.parse_command("")
    assert result.intent == nlp.INTENT_UNKNOWN


def test_whitespace_only_is_unknown():
    result = nlp.parse_command("   ")
    assert result.intent == nlp.INTENT_UNKNOWN


def test_nonsense_sentence_is_unknown():
    result = nlp.parse_command("the weather is nice today")
    assert result.intent == nlp.INTENT_UNKNOWN


def test_none_text_does_not_raise():
    result = nlp.parse_command(None)
    assert result.intent == nlp.INTENT_UNKNOWN


# --------------------------------------------------------------------------- #
# match_name -- fuzzy catalog matching
# --------------------------------------------------------------------------- #

def test_match_name_exact():
    assert nlp.match_name("milk", ["Milk", "Water"]) == "Milk"


def test_match_name_plural_variant():
    assert nlp.match_name("apple", ["Apples"]) == "Apples"


def test_match_name_typo_fuzzy_match():
    assert nlp.match_name("bananna", ["Bananas"]) == "Bananas"


def test_match_name_no_candidates_returns_none():
    assert nlp.match_name("milk", []) is None


def test_match_name_empty_query_returns_none():
    assert nlp.match_name("", ["Milk"]) is None
