"""Tests for Hindi command normalisation (backend/hindi.py) and its
integration into the main parser via nlp.parse_command.
"""

import hindi
import nlp


def test_contains_hindi_true_for_devanagari():
    assert hindi.contains_hindi("दूध जोड़ो") is True


def test_contains_hindi_false_for_english():
    assert hindi.contains_hindi("add milk") is False


def test_contains_hindi_false_for_empty():
    assert hindi.contains_hindi("") is False


def test_add_milk_hindi():
    assert hindi.to_english_command("दूध जोड़ो") == "add milk"


def test_add_five_apples_hindi():
    assert hindi.to_english_command("पांच सेब जोड़ो") == "add 5 apples"


def test_remove_milk_hindi():
    assert hindi.to_english_command("दूध हटाओ") == "remove milk"


def test_update_quantity_hindi():
    assert hindi.to_english_command("दूध की मात्रा 3 कर दो") == "set milk to 3"


def test_show_list_hindi():
    assert hindi.to_english_command("मेरी सूची दिखाओ") == "show my list"


def test_clear_list_hindi():
    assert hindi.to_english_command("मेरी सूची खाली करो") == "clear my list"


def test_recommend_hindi():
    assert hindi.to_english_command("मुझे क्या खरीदना चाहिए") == "show recommendations"


def test_search_with_max_price_hindi():
    result = hindi.to_english_command("300 रुपये से कम का टूथपेस्ट खोजो")
    assert result.startswith("find")
    assert "toothpaste" in result
    assert "under 300" in result


def test_asr_alias_seb_for_apple():
    """Speech recognition sometimes mis-hears सेब as the Latin "safe"."""
    assert hindi.to_english_command("safe जोड़ो") == "add apples"


def test_bare_product_word_defaults_to_add():
    """A bare Hindi product name with no recognised verb ("दूध") is treated
    as an implicit add, matching the documented behaviour in the README."""
    assert hindi.to_english_command("दूध") == "add milk"


def test_unrecognised_sentence_returns_empty():
    """Small talk with no known product word and no verb returns nothing,
    so the parser reports UNKNOWN instead of adding garbage to the list."""
    assert hindi.to_english_command("नमस्ते कैसे हो") == ""


# --------------------------------------------------------------------------- #
# End-to-end through nlp.parse_command, exactly as the API receives it
# --------------------------------------------------------------------------- #

def test_parse_command_hindi_add():
    result = nlp.parse_command("पांच सेब जोड़ो")
    assert result.intent == nlp.INTENT_ADD
    assert result.language == "hi"
    assert result.item == "apples"
    assert result.quantity == 5.0
    assert result.normalised_text == "add 5 apples"


def test_parse_command_hindi_remove():
    result = nlp.parse_command("दूध हटाओ")
    assert result.intent == nlp.INTENT_REMOVE
    assert result.language == "hi"
    assert result.item == "milk"


def test_parse_command_hindi_nonsense_is_unknown():
    result = nlp.parse_command("नमस्ते कैसे हो")
    assert result.intent == nlp.INTENT_UNKNOWN
    assert result.language == "hi"
