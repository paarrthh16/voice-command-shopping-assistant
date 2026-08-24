"""Executes a parsed voice or typed command.

This module is the bridge between the parser and the existing shopping-list
services. It contains no SQL and no list logic of its own: it decides which
existing service function a command maps to, then formats a confirmation the
user can read back.

    transcript -> nlp.parse_command -> this module -> services -> SQLite
"""

import re
from difflib import SequenceMatcher
from typing import Optional

import nlp
import recommendations
import services
from models import (
    CommandResponse,
    SearchFilters,
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
    SubstituteGroup,
)


# Units that never take a plural 's': measures and 'dozen'.
INVARIANT_UNITS = {"kg", "g", "l", "ml", "dozen"}
# Similarity at which one spoken word counts as one catalog word ("bananna").
WORD_CUTOFF = 0.75
IRREGULAR_PLURALS = {"loaf": "loaves", "box": "boxes", "pouch": "pouches"}


def _format_quantity(quantity: float) -> str:
    return str(int(quantity)) if float(quantity).is_integer() else str(quantity)


def _format_amount(quantity: float, unit: str) -> str:
    """Render '2 bottles', '1 kg' or plain '5' for countable pieces."""
    amount = _format_quantity(quantity)
    if not unit or unit == "piece":
        return amount
    if quantity == 1 or unit in INVARIANT_UNITS:
        return f"{amount} {unit}"
    return f"{amount} {IRREGULAR_PLURALS.get(unit, unit + 's')}"


def _describe(item) -> str:
    return f"{_format_amount(item.quantity, item.unit)} {item.name}"


def process_command(text: str) -> CommandResponse:
    """Parse a command, run it against the shopping list and describe the result."""
    parsed = nlp.parse_command(text)

    result = CommandResponse(
        transcript=text,
        intent=parsed.intent,
        language=parsed.language,
        understood_as=parsed.normalised_text,
        item=parsed.item,
        quantity=parsed.quantity,
        unit=parsed.unit,
        success=False,
        message="I couldn't understand that command.",
        items=[],
    )

    handler = {
        nlp.INTENT_ADD: _handle_add,
        nlp.INTENT_REMOVE: _handle_remove,
        nlp.INTENT_UPDATE: _handle_update,
        nlp.INTENT_SHOW: _handle_show,
        nlp.INTENT_CLEAR: _handle_clear,
        nlp.INTENT_SEARCH: _handle_search,
        nlp.INTENT_RECOMMEND: _handle_recommend,
    }.get(parsed.intent)

    if handler is not None:
        handler(parsed, result)

    result.items = services.get_shopping_list()
    return result


def _list_item_names() -> list:
    return [item.name for item in services.get_shopping_list()]


def _match_catalog(name: Optional[str]) -> Optional[str]:
    return nlp.match_name(name, services.product_names()) if name else None


# --------------------------------------------------------------------------- #
# Catalog resolution for ADD
#
# The shop can only sell what it stocks, so an add command has to resolve to a
# real catalog product. Fuzzy matching still applies ("bananna" -> Bananas), but
# a match is only accepted when the catalog name accounts for what was said:
# "chocolate cake" must not quietly become Chocolate.
# --------------------------------------------------------------------------- #

def _ratio(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def _same_word(word: str, other: str) -> bool:
    """One spoken word and one catalog word meaning the same thing."""
    return (
        word == other
        or word.rstrip("s") == other.rstrip("s")
        or _ratio(word, other) >= WORD_CUTOFF
    )


def _brand_keys() -> set:
    """Every word used by a catalog brand, punctuation removed ("Lay's" -> lays)."""
    return {
        re.sub(r"[^a-z0-9]", "", nlp.normalise(word))
        for brand in services.brand_names()
        for word in brand.split()
    } - {""}


def _is_brand_word(word: str, brand_keys: set) -> bool:
    key = re.sub(r"[^a-z0-9]", "", word)
    if not key:
        return True
    return any(key == brand or (len(key) >= 3 and key in brand) for brand in brand_keys)


def _explains(query: str, candidate: str, brand_keys: set) -> bool:
    """True when `candidate` accounts for every meaningful word of `query`.

    Brand words and one- or two-letter fragments are ignored ("lays potato
    chips", "parle g biscuits"), but at least one word must match the product
    name itself, so a bare brand resolves to nothing.
    """
    candidate_words = nlp.normalise(candidate).split()
    matched = False
    for word in query.split():
        if any(_same_word(word, catalog_word) for catalog_word in candidate_words):
            matched = True
        elif len(word) > 2 and not _is_brand_word(word, brand_keys):
            return False
    return matched


def _resolve_catalog_product(spoken: Optional[str]) -> Optional[str]:
    """Return the catalog product name for a spoken item, or None if unstocked."""
    if not spoken or not spoken.strip():
        return None

    _brand, remainder = nlp.extract_brand(spoken, services.brand_names())
    query = nlp.normalise(remainder or spoken)
    if not query:
        return None

    brand_keys = _brand_keys()
    candidates = [
        name for name in services.product_names() if _explains(query, name, brand_keys)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda name: (_ratio(query, nlp.normalise(name)), -len(name)))


# --------------------------------------------------------------------------- #
# Intent handlers
# --------------------------------------------------------------------------- #

def _handle_add(parsed, result: CommandResponse) -> None:
    quantity = parsed.quantity or 1
    catalog_name = _resolve_catalog_product(parsed.item)

    if catalog_name is None:
        # Nothing is written: no list row, no history, no "Other" category.
        spoken = (parsed.item or "").strip()
        result.matched_product = None
        result.success = False
        result.message = (
            f"{spoken.title()} is not available in our shop, so I didn't add it."
            if spoken
            else "I couldn't tell which product you meant, so I didn't add anything."
        )
        return

    already_listed = services.find_item_by_name(catalog_name) is not None

    payload = ShoppingListItemCreate(
        name=catalog_name,
        quantity=quantity,
        unit=parsed.unit,
    )
    try:
        # catalog_only is the guard at the insert itself: even if the resolution
        # above ever let something through, no unstocked row can be created.
        item = services.add_item(payload, catalog_only=True)
    except services.ServiceError as error:
        result.matched_product = None
        result.success = False
        result.message = error.message
        return

    result.matched_product = item.name
    result.item = item.name
    result.quantity = item.quantity
    result.unit = item.unit
    result.success = True
    if already_listed:
        # services.add_item merges repeats into the existing row, so say the
        # running total rather than implying a second entry was created.
        result.message = f"{item.name} is now {_format_amount(item.quantity, item.unit)} on your list."
    else:
        result.message = f"Added {_describe(item)} to your list."


def _handle_remove(parsed, result: CommandResponse) -> None:
    match = nlp.match_name(parsed.item, _list_item_names())

    if match is None:
        catalog_name = _match_catalog(parsed.item)
        result.message = (
            f"{catalog_name} isn't on your list."
            if catalog_name
            else "I couldn't find that product."
        )
        return

    item = services.find_item_by_name(match)
    services.delete_item(item.id)

    result.matched_product = match
    result.item = match
    result.success = True
    result.message = f"Removed {match} from your list."


def _handle_update(parsed, result: CommandResponse) -> None:
    match = nlp.match_name(parsed.item, _list_item_names())

    if match is None:
        result.message = (
            f"{parsed.item} isn't on your list, so there's nothing to update."
            if parsed.item
            else "I couldn't find that product."
        )
        return

    item = services.find_item_by_name(match)
    updated = services.update_item(
        item.id, ShoppingListItemUpdate(quantity=parsed.quantity, unit=parsed.unit)
    )

    result.matched_product = match
    result.item = updated.name
    result.quantity = updated.quantity
    result.unit = updated.unit
    result.success = True
    result.message = f"Updated {updated.name} to {_format_amount(updated.quantity, updated.unit)}."


def _handle_show(parsed, result: CommandResponse) -> None:
    items = services.get_shopping_list()
    pending = [item for item in items if not item.completed]

    result.success = True
    if not items:
        result.message = "Your shopping list is empty."
    else:
        result.message = "On your list: " + ", ".join(_describe(item) for item in pending) + "."
        if not pending:
            result.message = "Everything on your list is already ticked off."


def _describe_filters(filters: SearchFilters) -> str:
    """Summarise the active filters for the confirmation line."""
    parts = []
    if filters.query:
        parts.append(f"“{filters.query}”")
    if filters.brand:
        parts.append(f"brand {filters.brand}")
    if filters.size:
        parts.append(f"size {filters.size}")
    if filters.min_price is not None and filters.max_price is not None:
        parts.append(f"₹{_format_quantity(filters.min_price)}–₹{_format_quantity(filters.max_price)}")
    elif filters.max_price is not None:
        parts.append(f"under ₹{_format_quantity(filters.max_price)}")
    elif filters.min_price is not None:
        parts.append(f"over ₹{_format_quantity(filters.min_price)}")
    return ", ".join(parts)


def _handle_search(parsed, result: CommandResponse) -> None:
    parsed_filters = parsed.filters
    brand, query = nlp.extract_brand(parsed_filters.query, services.brand_names())

    filters = SearchFilters(
        query=query,
        brand=brand,
        size=parsed_filters.size,
        min_price=parsed_filters.min_price,
        max_price=parsed_filters.max_price,
    )
    result.filters = filters

    matches = services.search_products(
        query=filters.query,
        brand=filters.brand,
        size=filters.size,
        min_price=filters.min_price,
        max_price=filters.max_price,
    )

    # A misheard or unusual product name still deserves results, so fall back to
    # the same fuzzy matcher the other intents use before giving up.
    if not matches and filters.query:
        closest = nlp.match_name(filters.query, services.product_names())
        if closest:
            matches = services.search_products(
                query=closest,
                brand=filters.brand,
                size=filters.size,
                min_price=filters.min_price,
                max_price=filters.max_price,
            )

    result.results = matches
    result.substitutes = _substitutes_for(matches)
    result.success = bool(matches)
    summary = _describe_filters(filters)

    if matches:
        result.message = (
            f"Found {len(matches)} product{'s' if len(matches) != 1 else ''}"
            f"{f' for {summary}' if summary else ''}."
        )
    else:
        result.message = (
            f"No products found{f' for {summary}' if summary else ''}. "
            "Try changing the brand, size or price range."
        )


def _substitutes_for(products) -> list:
    """Offer alternatives for any unavailable product in a result set.

    All substitute names are fetched in a single query rather than one query
    per product.
    """
    unavailable = [product for product in products if not product.available]
    if not unavailable:
        return []

    wanted = [name for product in unavailable for name in product.substitutes]
    catalog = {product.name.lower(): product for product in services.products_by_names(wanted)}

    groups = []
    for product in unavailable:
        alternatives = [
            catalog[name.lower()]
            for name in product.substitutes
            if name.lower() in catalog and catalog[name.lower()].available
        ]
        if alternatives:
            groups.append(SubstituteGroup(for_product=product.name, alternatives=alternatives))
    return groups


def _handle_recommend(parsed, result: CommandResponse) -> None:
    suggestions = recommendations.build_recommendations(limit=6)
    result.recommendations = suggestions.recommendations
    result.success = bool(suggestions.recommendations)
    if suggestions.recommendations:
        top = ", ".join(entry.product.name for entry in suggestions.recommendations[:3])
        result.message = f"{suggestions.message} Top picks: {top}."
    else:
        result.message = "I don't have any suggestions right now."


def _handle_clear(parsed, result: CommandResponse) -> None:
    removed = services.clear_list()
    result.success = True
    result.message = (
        f"Cleared your list ({removed} item{'s' if removed != 1 else ''} removed)."
        if removed
        else "Your list was already empty."
    )
