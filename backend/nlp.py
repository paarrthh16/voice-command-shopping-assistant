"""Rule-based natural language processing for shopping commands.

The parser is deliberately small and inspectable: no ML model, no external
service, no third-party dependency. It runs in four steps.

    normalise  ->  detect intent  ->  extract entities  ->  match the catalog

`parse_command()` is pure: it reads text and returns a `ParsedCommand`. It never
touches the database. Executing the command is the job of `commands.py`.
"""

import re
from dataclasses import dataclass, field
from difflib import get_close_matches
from typing import Dict, List, Optional

import hindi

# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #

NUMBER_WORDS: Dict[str, int] = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "hundred": 100,
    "couple": 2, "dozen": 12,
}

# Each unit maps to the singular form used by the product catalog.
UNIT_ALIASES: Dict[str, str] = {
    "bottle": "bottle", "bottles": "bottle",
    "packet": "pack", "packets": "pack", "pack": "pack", "packs": "pack",
    "box": "box", "boxes": "box",
    "can": "can", "cans": "can",
    "jar": "jar", "jars": "jar",
    "tube": "tube", "tubes": "tube",
    "bar": "bar", "bars": "bar",
    "cup": "cup", "cups": "cup",
    "carton": "carton", "cartons": "carton",
    "pouch": "pouch", "pouches": "pouch",
    "roll": "roll", "rolls": "roll",
    "loaf": "loaf", "loaves": "loaf",
    "bunch": "bunch", "bunches": "bunch",
    "dozen": "dozen", "dozens": "dozen",
    "piece": "piece", "pieces": "piece", "pcs": "piece",
    "kg": "kg", "kilo": "kg", "kilos": "kg", "kilogram": "kg", "kilograms": "kg",
    "g": "g", "gram": "g", "grams": "g",
    "l": "l", "litre": "l", "litres": "l", "liter": "l", "liters": "l",
    "ml": "ml",
}

# Intent patterns are tried in this order; the first match wins. Order matters:
# "remove everything" must be read as CLEAR_LIST, not REMOVE_ITEM.
CLEAR_PATTERNS = [
    r"\b(?:clear|empty|reset|wipe)\b.*\b(?:list|everything|all)\b",
    r"\b(?:remove|delete)\b.*\b(?:everything|all items|all of it|the whole list)\b",
    r"^(?:clear|start over|start again)$",
]

SHOW_PATTERNS = [
    r"\b(?:show|display|read|tell me|see|check)\b.*\b(?:list|items|cart)\b",
    r"\bwhat(?:'s| is| do i have| have i got)\b.*\b(?:list|need|cart)\b",
    r"^(?:my list|the list|shopping list)$",
]

# Each entry is a regex whose `obj` group holds the part of the sentence that
# names the product (and possibly its quantity and unit).
UPDATE_PATTERNS = [
    # qty captures the rest of the line ("2 litres", not just "2"), so a unit
    # spoken alongside the number is not left dangling and read as UNKNOWN.
    r"^(?:change|set|update|make)\s+(?:the\s+)?(?P<obj>.+?)\s+(?:quantity\s+)?(?:to|=)\s+(?P<qty>.+)$",
    r"^(?:change|set|update|make)\s+(?:the\s+)?(?P<obj>.+?)\s+quantity\s+(?P<qty>.+)$",
    # No connector word at all ("make water 3 bottles"): qty must start with a
    # digit, so the non-greedy obj still stops at the right place.
    r"^(?:change|set|update|make)\s+(?:the\s+)?(?P<obj>.+?)\s+(?P<qty>\d.*)$",
    r"^i\s+(?:need|want)\s+(?P<qty>[\w.]+)\s+(?P<obj>.+?)\s+instead$",
]

REMOVE_PATTERNS = [
    r"^(?:please\s+)?(?:remove|delete|drop|erase|cancel)\s+(?P<obj>.+?)"
    r"(?:\s+(?:from|off)\s+(?:of\s+)?(?:my|the)?\s*(?:shopping\s+)?list)?$",
    r"^take\s+(?P<obj>.+?)\s+(?:off|out)(?:\s+(?:of\s+)?(?:my|the)?\s*(?:shopping\s+)?list)?$",
    r"^get\s+rid\s+of\s+(?P<obj>.+)$",
    # obj is non-greedy with an optional trailing "anymore", so "I don't need
    # milk anymore" resolves to the item "milk", not "milk anymore".
    r"^i\s+(?:don't|dont|do not)\s+need\s+(?P<obj>.+?)(?:\s+any\s*more)?$",
]

ADD_PATTERNS = [
    r"^(?:please\s+)?add\s+(?P<obj>.+?)"
    r"(?:\s+(?:to|on|in)\s+(?:my|the)?\s*(?:shopping\s+)?list)?$",
    r"^put\s+(?P<obj>.+?)\s+(?:on|in|into)\s+(?:my|the)?\s*(?:shopping\s+)?(?:list|cart)$",
    r"^i\s+(?:need|want|would like|will need)\s+(?:to\s+(?:buy|get|add|purchase|order)\s+)?(?P<obj>.+)$",
    r"^(?:buy|get|purchase|order|grab|pick up)\s+(?P<obj>.+)$",
    r"^(?:we|i)\s+(?:are|am)\s+out\s+of\s+(?P<obj>.+)$",
]

# Trailing phrases that carry no product information.
TRAILING_NOISE = re.compile(
    r"\s+(?:to|on|in|from|off)\s+(?:my|the)?\s*(?:shopping\s+)?(?:list|cart)$"
)

# Smart suggestions. Checked before the search patterns, because "show
# recommendations" would otherwise be read as a search for a product called
# "recommendations".
RECOMMEND_PATTERNS = [
    r"\b(?:recommend|recommendations?|suggest|suggestions?|ideas?)\b",
    r"\bwhat should i (?:buy|get)\b",
]

# Product search. Checked after SHOW_LIST so that "show my list" stays a list
# command while "show me toothpaste" becomes a search.
SEARCH_PATTERNS = [
    r"^(?:find|search|look)\s+(?:for\s+)?(?:me\s+)?(?P<obj>.+)$",
    r"^show\s+(?:me\s+)?(?P<obj>.+)$",
    r"^(?:do you have|have you got)\s+(?:any\s+)?(?P<obj>.+)$",
    r"^(?:is|are)\s+there\s+(?:any\s+)?(?P<obj>.+)$",
]

# Money written as '₹300', 'rs 300', '300 rupees' or plain '300'.
_PRICE = r"(?:₹|rs\.?|inr|\$)?\s*(\d+(?:\.\d+)?)\s*(?:rupees?|rs\.?|inr|dollars?)?"

PRICE_RANGE_PATTERNS = [
    rf"\bbetween\s+{_PRICE}\s+(?:and|to)\s+{_PRICE}",
    rf"\bfrom\s+{_PRICE}\s+(?:to|and)\s+{_PRICE}",
    rf"\bin\s+the\s+range\s+(?:of\s+)?{_PRICE}\s*(?:to|-|and)\s*{_PRICE}",
]

MAX_PRICE_PATTERNS = [
    rf"\b(?:under|below|less than|lower than|cheaper than|within|upto|up to|at most|"
    rf"not more than|max|maximum(?: of)?)\s+{_PRICE}",
]

MIN_PRICE_PATTERNS = [
    rf"\b(?:over|above|more than|higher than|at least|starting (?:from|at)|"
    rf"min|minimum(?: of)?)\s+{_PRICE}",
]

# '100g', '100 grams', '1 kg', '500 ml' -> normalised to '<number> <unit>'.
SIZE_PATTERN = (
    r"\b(\d+(?:\.\d+)?)\s*(kg|kilograms?|kilos?|kilogrammes?|gm|grams?|g|"
    r"millilitres?|milliliters?|ml|litres?|liters?|l)\b"
)

SIZE_UNITS = {
    "kg": "kg", "kilo": "kg", "kilos": "kg", "kilogram": "kg", "kilograms": "kg",
    "kilogramme": "kg", "kilogrammes": "kg",
    "g": "g", "gm": "g", "gram": "g", "grams": "g",
    "ml": "ml", "millilitre": "ml", "millilitres": "ml",
    "milliliter": "ml", "milliliters": "ml",
    "l": "l", "litre": "l", "litres": "l", "liter": "l", "liters": "l",
}

# Comparison words left behind when no number followed them, e.g. a misheard
# "toothpaste under abc". Removed so they are not treated as product words.
DANGLING_COMPARISON = re.compile(
    r"\b(?:under|below|over|above|between|upto|up to|at most|at least|less than|"
    r"more than|cheaper than|within|max|maximum|min|minimum)\b"
)

# Words that add nothing once the filters have been pulled out.
SEARCH_NOISE = re.compile(
    r"\b(?:some|any|the|a|an|please|products?|items?|in|size|priced?|cost(?:ing)?|"
    r"for|available|options?)\b"
)

INTENT_ADD = "ADD_ITEM"
INTENT_REMOVE = "REMOVE_ITEM"
INTENT_UPDATE = "UPDATE_ITEM"
INTENT_SHOW = "SHOW_LIST"
INTENT_CLEAR = "CLEAR_LIST"
INTENT_SEARCH = "SEARCH_PRODUCT"
INTENT_RECOMMEND = "RECOMMEND"
INTENT_UNKNOWN = "UNKNOWN"


@dataclass
class SearchFilters:
    """Filters pulled out of a search command. All fields are optional."""

    query: Optional[str] = None
    brand: Optional[str] = None
    size: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None


@dataclass
class ParsedCommand:
    intent: str
    text: str
    language: str = "en"
    normalised_text: Optional[str] = None
    item: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    filters: Optional[SearchFilters] = None
    matches: Dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #

CONTRACTIONS = {
    "i'd like": "i would like",
    "i'm": "i am",
    "we're": "we are",
    "gimme": "give me",
    "wanna": "want to",
    "lemme": "let me",
}


def normalise(text: str) -> str:
    """Lowercase, expand a few contractions and strip punctuation."""
    lowered = (text or "").lower().strip()
    for contraction, expansion in CONTRACTIONS.items():
        lowered = lowered.replace(contraction, expansion)
    # Devanagari combining marks are not word characters, so the range is kept
    # explicitly: without it "अचार" would lose its vowel signs.
    lowered = re.sub(r"[^\w\s.'\-ऀ-ॿ]", " ", lowered)
    lowered = re.sub(r"\bplease\b", " ", lowered)
    # A polite wrapper carries no intent of its own: "can you add milk"
    # should reach the same ADD_PATTERNS as "add milk".
    lowered = re.sub(r"^(?:can|could|would) you\s+", "", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _to_number(token: str) -> Optional[float]:
    """Convert '5', '2.5' or 'five' into a number, else None."""
    token = token.strip().lower()
    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return float(token)
    return float(NUMBER_WORDS[token]) if token in NUMBER_WORDS else None


# --------------------------------------------------------------------------- #
# Entity extraction
# --------------------------------------------------------------------------- #

def extract_entities(phrase: str) -> Dict[str, Optional[object]]:
    """Pull quantity, unit and item name out of the object part of a command.

    Handles '5 apples', '2 bottles of water', 'a dozen eggs' and plain 'milk'.
    """
    phrase = TRAILING_NOISE.sub("", phrase.strip())
    tokens = phrase.split()
    quantity: Optional[float] = None
    unit: Optional[str] = None

    if tokens:
        value = _to_number(tokens[0])
        # 'dozen eggs' means twelve; 'dozen' alone is the unit, not the item.
        if value is not None and not (tokens[0] in UNIT_ALIASES and len(tokens) == 1):
            quantity = value
            tokens = tokens[1:]

    if tokens and tokens[0] in UNIT_ALIASES:
        unit = UNIT_ALIASES[tokens[0]]
        tokens = tokens[1:]
        if tokens and tokens[0] == "of":
            tokens = tokens[1:]

    # A trailing quantity, as in 'apples 5'.
    if quantity is None and len(tokens) > 1:
        value = _to_number(tokens[-1])
        if value is not None:
            quantity = value
            tokens = tokens[:-1]

    item = " ".join(tokens).strip(" .-")
    return {"item": item or None, "quantity": quantity, "unit": unit}


# --------------------------------------------------------------------------- #
# Search filters
# --------------------------------------------------------------------------- #

def _normalise_size(number: str, unit: str) -> str:
    value = float(number)
    amount = str(int(value)) if value.is_integer() else str(value)
    return f"{amount} {SIZE_UNITS.get(unit, unit)}"


def extract_search_filters(phrase: str) -> SearchFilters:
    """Pull price, size and remaining query text out of a search phrase.

    Each filter is removed from the phrase as it is recognised, so whatever is
    left over is the product text ("colgate toothpaste", "organic apples").
    """
    text = phrase.strip()
    filters = SearchFilters()

    # A range must be read before 'from X' is mistaken for a minimum price.
    for pattern in PRICE_RANGE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            low, high = float(match.group(1)), float(match.group(2))
            filters.min_price, filters.max_price = min(low, high), max(low, high)
            text = text[: match.start()] + " " + text[match.end() :]
            break

    if filters.max_price is None:
        for pattern in MAX_PRICE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                filters.max_price = float(match.group(1))
                text = text[: match.start()] + " " + text[match.end() :]
                break

    if filters.min_price is None:
        for pattern in MIN_PRICE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                filters.min_price = float(match.group(1))
                text = text[: match.start()] + " " + text[match.end() :]
                break

    size_match = re.search(SIZE_PATTERN, text)
    if size_match:
        filters.size = _normalise_size(size_match.group(1), size_match.group(2))
        text = text[: size_match.start()] + " " + text[size_match.end() :]

    remainder = DANGLING_COMPARISON.sub(" ", text)
    remainder = SEARCH_NOISE.sub(" ", remainder)
    remainder = re.sub(r"\s+", " ", remainder).strip(" .,-")
    filters.query = remainder or None
    return filters


def extract_brand(query: Optional[str], known_brands: List[str]) -> tuple:
    """Split a brand name out of the query text.

    The catalog supplies the brand vocabulary, so this stays a pure function:
    it never reads the database itself.
    """
    if not query:
        return None, query

    normalised = normalise(query)
    # Longest brand first, so 'Organic Harvest' wins over a shorter substring.
    for brand in sorted(known_brands, key=len, reverse=True):
        brand_key = normalise(brand)
        if not brand_key:
            continue
        pattern = rf"(?<!\w){re.escape(brand_key)}(?!\w)"
        if re.search(pattern, normalised):
            remainder = re.sub(pattern, " ", normalised)
            remainder = re.sub(r"\s+", " ", remainder).strip()
            return brand, remainder or None
    return None, query


# --------------------------------------------------------------------------- #
# Intent detection
# --------------------------------------------------------------------------- #

def parse_command(text: str) -> ParsedCommand:
    """Turn a raw transcript into a structured command, in English or Hindi.

    Hindi is rewritten as the equivalent English command first, so both
    languages share one parser, one set of intents and one set of services.
    """
    if hindi.contains_hindi(text):
        english = hindi.to_english_command(text)
        parsed = _parse(text, normalise(english))
        parsed.language = "hi"
        parsed.normalised_text = english or None
        return parsed
    return _parse(text, normalise(text))


def _parse(text: str, normalised: str) -> ParsedCommand:
    """Match the normalised English text against the intent patterns."""
    if not normalised:
        return ParsedCommand(intent=INTENT_UNKNOWN, text=text)

    for pattern in CLEAR_PATTERNS:
        if re.search(pattern, normalised):
            return ParsedCommand(intent=INTENT_CLEAR, text=text)

    for pattern in SHOW_PATTERNS:
        if re.search(pattern, normalised):
            return ParsedCommand(intent=INTENT_SHOW, text=text)

    for pattern in RECOMMEND_PATTERNS:
        if re.search(pattern, normalised):
            return ParsedCommand(intent=INTENT_RECOMMEND, text=text)

    for pattern in SEARCH_PATTERNS:
        match = re.match(pattern, normalised)
        if match:
            filters = extract_search_filters(match.group("obj"))
            if filters.query or filters.max_price or filters.min_price or filters.size:
                return ParsedCommand(intent=INTENT_SEARCH, text=text, filters=filters)

    for pattern in UPDATE_PATTERNS:
        match = re.match(pattern, normalised)
        if match:
            entities = extract_entities(match.group("obj"))
            # The quantity side may carry its own unit ("to 2 litres"), so it
            # is parsed the same way as an ADD/REMOVE object rather than read
            # as a single bare number.
            qty_entities = extract_entities(match.group("qty"))
            quantity = qty_entities["quantity"]
            if quantity is None:
                quantity = _to_number(match.group("qty").strip())
            unit = qty_entities["unit"] or entities["unit"]
            if quantity is not None:
                return ParsedCommand(
                    intent=INTENT_UPDATE,
                    text=text,
                    item=entities["item"],
                    quantity=quantity,
                    unit=unit,
                )

    for pattern in REMOVE_PATTERNS:
        match = re.match(pattern, normalised)
        if match:
            entities = extract_entities(match.group("obj"))
            if entities["item"]:
                return ParsedCommand(
                    intent=INTENT_REMOVE,
                    text=text,
                    item=entities["item"],
                    quantity=entities["quantity"],
                    unit=entities["unit"],
                )

    for pattern in ADD_PATTERNS:
        match = re.match(pattern, normalised)
        if match:
            entities = extract_entities(match.group("obj"))
            if entities["item"]:
                return ParsedCommand(
                    intent=INTENT_ADD,
                    text=text,
                    item=entities["item"],
                    quantity=entities["quantity"],
                    unit=entities["unit"],
                )

    return ParsedCommand(intent=INTENT_UNKNOWN, text=text)


# --------------------------------------------------------------------------- #
# Name matching
# --------------------------------------------------------------------------- #

def _variants(name: str) -> List[str]:
    """Naive singular/plural variants so 'apple' can match 'Apples'."""
    base = normalise(name)
    forms = {base}
    if base.endswith("ies"):
        forms.add(base[:-3] + "y")
    if base.endswith("es"):
        forms.add(base[:-2])
    if base.endswith("s"):
        forms.add(base[:-1])
    else:
        forms.update({base + "s", base + "es"})
    return [form for form in forms if form]


def match_name(query: str, candidates: List[str], cutoff: float = 0.75) -> Optional[str]:
    """Find the best candidate name for a spoken product name.

    Tried in order: exact match, singular/plural variant, substring, then
    difflib similarity so that 'bananna' still reaches 'Bananas'.
    """
    if not query or not candidates:
        return None

    normalised_query = normalise(query)
    index: Dict[str, str] = {}
    for candidate in candidates:
        for form in _variants(candidate):
            index.setdefault(form, candidate)

    if normalised_query in index:
        return index[normalised_query]

    for form in _variants(normalised_query):
        if form in index:
            return index[form]

    # Substring both ways: 'organic apple' -> 'Organic Apples', 'milk' -> 'Milk'.
    contained = [
        candidate
        for candidate in candidates
        if normalised_query in normalise(candidate) or normalise(candidate) in normalised_query
    ]
    if contained:
        return min(contained, key=lambda candidate: len(candidate))

    close = get_close_matches(normalised_query, list(index.keys()), n=1, cutoff=cutoff)
    return index[close[0]] if close else None
