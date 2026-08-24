"""Hindi support for the command parser.

Rather than a second parser or a translation API, Hindi is handled by a small
normalisation layer: a Hindi sentence is rewritten as the equivalent canonical
English command, which then goes through the *same* parser, the same intents
and the same services as English.

    "दो बोतल पानी जोड़ो"  ->  "add 2 bottle water"  ->  ADD_ITEM / water / 2 / bottle

Hindi is verb-final while the English patterns are verb-first, so the rewrite
also reorders: the intent verb is detected anywhere in the sentence, removed,
and re-emitted at the front.

Everything here is a dictionary lookup. No model, no network call, no API key.
"""

import re
from typing import Dict, List, Optional, Tuple

DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# Hindi digits, occasionally returned by speech recognition.
DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

NUMBERS: Dict[str, int] = {
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5,
    "छह": 6, "छः": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "ग्यारह": 11, "बारह": 12, "आधा": 1, "दर्जन": 12,
}

UNITS: Dict[str, str] = {
    "बोतल": "bottle", "किलो": "kg", "किलोग्राम": "kg", "ग्राम": "g",
    "लीटर": "l", "मिलीलीटर": "ml", "पैकेट": "pack", "पैक": "pack",
    "डिब्बा": "box", "डिब्बे": "box", "दर्जन": "dozen", "पीस": "piece",
    "गुच्छा": "bunch", "टुकड़ा": "piece", "कप": "cup", "ट्यूब": "tube",
}

# Common demo products only -- the catalog itself stays in English.
PRODUCTS: Dict[str, str] = {
    "दूध": "milk", "पानी": "water", "सेब": "apples", "केला": "bananas",
    "केले": "bananas", "चावल": "rice", "रोटी": "bread", "ब्रेड": "bread",
    "डबलरोटी": "bread", "टूथपेस्ट": "toothpaste", "टूथब्रश": "toothbrush",
    "साबुन": "soap", "शैम्पू": "shampoo", "शैंपू": "shampoo",
    "दही": "curd", "पनीर": "paneer", "मक्खन": "butter", "चीज़": "cheese slices",
    "चाय": "tea", "कॉफ़ी": "coffee", "कॉफी": "coffee", "जूस": "orange juice",
    "बिस्किट": "biscuits", "बिस्कुट": "biscuits", "चॉकलेट": "chocolate",
    "नमकीन": "namkeen", "चिप्स": "potato chips", "बादाम": "almonds",
    "काजू": "cashews", "पॉपकॉर्न": "popcorn",
    "आलू": "potatoes", "प्याज": "onions", "प्याज़": "onions",
    "टमाटर": "tomatoes", "पालक": "spinach", "मेथी": "fenugreek leaves",
    "संतरा": "oranges", "संतरे": "oranges", "आम": "mangoes",
    "मौसंबी": "sweet lime", "कोला": "cola", "सोडा": "soda",
    "डिटर्जेंट": "detergent", "सर्फ": "detergent", "हैंडवाश": "handwash",
    "टॉयलेट": "toilet paper", "फॉयल": "aluminium foil",
    "जैविक": "organic", "ऑर्गेनिक": "organic",
}

# Speech recognition sometimes returns a Hindi word as a Latin-script
# approximation of how it sounded -- "सेब" commonly comes back as "safe" or
# "seb". These aliases are consulted ONLY on the Hindi path, so an English
# command such as "add safe" is unaffected.
ASR_ALIASES: Dict[str, str] = {
    # सेब (apple)
    "seb": "apples", "safe": "apples", "saib": "apples", "sebh": "apples",
    # दूध (milk)
    "doodh": "milk", "dudh": "milk", "dood": "milk",
    # पानी (water)
    "paani": "water", "pani": "water",
    # केला (banana)
    "kela": "bananas", "kele": "bananas",
    # चावल (rice)
    "chawal": "rice", "chaawal": "rice",
    # रोटी (bread)
    "roti": "bread",
    # आलू / प्याज / टमाटर
    "aloo": "potatoes", "alu": "potatoes",
    "pyaz": "onions", "pyaaz": "onions",
    "tamatar": "tomatoes",
}

# Words that carry no meaning once the command has been understood.
FILLERS = {
    "मेरी", "मेरा", "मेरे", "मुझे", "मुझको", "कृपया", "सूची", "लिस्ट", "में",
    "से", "का", "की", "के", "को", "है", "हैं", "और", "वाला", "वाली", "साइज",
    "साइज़", "यह", "वो", "अब", "जरा", "ज़रा", "थोड़ा", "कुछ", "पर", "खरीदारी",
    "शॉपिंग", "सामान", "चीज़", "चीज", "रुपये", "रुपए", "रुपया", "रु",
}

# Intent phrases, longest first so "खाली कर दो" beats "कर दो".
INTENT_PHRASES: List[Tuple[str, str]] = [
    # Recommendations -- checked first: "क्या खरीदना चाहिए" also contains a buy verb.
    ("क्या खरीदना चाहिए", "RECOMMEND"),
    ("क्या खरीदूं", "RECOMMEND"),
    ("सुझाव दो", "RECOMMEND"),
    ("सुझाव दिखाओ", "RECOMMEND"),
    ("सुझाव", "RECOMMEND"),
    ("सिफारिश", "RECOMMEND"),
    ("रेकमेंडेशन", "RECOMMEND"),
    # Clear -- before UPDATE, because "खाली कर दो" ends in "कर दो".
    ("खाली कर दो", "CLEAR"),
    ("खाली करो", "CLEAR"),
    ("साफ कर दो", "CLEAR"),
    ("साफ करो", "CLEAR"),
    ("सब हटा दो", "CLEAR"),
    ("सब कुछ हटाओ", "CLEAR"),
    # Search
    ("खोज कर दो", "SEARCH"),
    ("सर्च करो", "SEARCH"),
    ("खोजो", "SEARCH"),
    ("खोजें", "SEARCH"),
    ("ढूंढो", "SEARCH"),
    ("ढूँढो", "SEARCH"),
    ("ढूंढें", "SEARCH"),
    # Show list. The bare verbs are ambiguous -- "सूची दिखाओ" is the list but
    # "टूथपेस्ट दिखाओ" is a search and "मुझे मौसम बताओ" is neither -- so they
    # are resolved after the sentence has been stripped, in _resolve_show.
    ("सूची दिखाओ", "SHOW"),
    ("लिस्ट दिखाओ", "SHOW"),
    ("दिखाओ", "SHOW_OR_SEARCH"),
    ("दिखाइए", "SHOW_OR_SEARCH"),
    ("बताओ", "SHOW_OR_SEARCH"),
    # Update
    ("मात्रा", "UPDATE"),
    ("बदल दो", "UPDATE"),
    ("बदलो", "UPDATE"),
    ("कर दो", "UPDATE"),
    ("कर दीजिए", "UPDATE"),
    # Remove
    ("हटा दो", "REMOVE"),
    ("हटाओ", "REMOVE"),
    ("हटाएं", "REMOVE"),
    ("निकाल दो", "REMOVE"),
    ("निकालो", "REMOVE"),
    ("मिटाओ", "REMOVE"),
    ("डिलीट करो", "REMOVE"),
    # Add
    ("जोड़ दो", "ADD"),
    ("जोड़ो", "ADD"),
    ("जोड़ें", "ADD"),
    ("जोड़िए", "ADD"),
    ("डाल दो", "ADD"),
    ("डालो", "ADD"),
    ("ऐड करो", "ADD"),
    ("एड करो", "ADD"),
    ("खरीदना है", "ADD"),
    ("लाना है", "ADD"),
    ("चाहिए", "ADD"),
    ("लेना है", "ADD"),
]

# Price comparisons: "300 से कम" -> under 300.
MAX_PRICE_WORDS = ["से कम", "से नीचे", "से सस्ता", "तक"]
MIN_PRICE_WORDS = ["से ज्यादा", "से ज़्यादा", "से अधिक", "से ऊपर", "से महंगा"]

# The English command each intent produces.
ENGLISH_VERBS = {
    "ADD": "add",
    "REMOVE": "remove",
    "SEARCH": "find",
    "SHOW": "show my list",
    "CLEAR": "clear my list",
    "RECOMMEND": "show recommendations",
}


def contains_hindi(text: str) -> bool:
    """True when the text contains Devanagari characters."""
    return bool(DEVANAGARI.search(text or ""))


def _clean(text: str) -> str:
    text = (text or "").translate(DEVANAGARI_DIGITS)
    text = re.sub(r"[^\w\sऀ-ॿ]", " ", text)
    return " " + re.sub(r"\s+", " ", text).strip() + " "


# Words that mean "the shopping list" rather than a product.
LIST_WORDS = {"सूची", "लिस्ट", "खरीदारी", "सामान"}


def _resolve_show(text: str) -> Optional[str]:
    """Decide what a bare "दिखाओ" / "बताओ" actually asked for.

    A list word means the shopping list; a known product means a search;
    anything else -- "मुझे मौसम बताओ" -- is not a shopping command at all.
    """
    tokens = text.split()
    if any(token in LIST_WORDS for token in tokens):
        return "SHOW"
    if any(is_known_product(token) for token in tokens):
        return "SEARCH"
    return None


def _detect_intent(text: str) -> Tuple[Optional[str], str]:
    """Find the intent phrase, remove it, and return (intent, remaining text).

    The scan repeats so that a sentence carrying two markers of the same
    intent -- "... की मात्रा 3 कर दो" holds both 'मात्रा' and 'कर दो' -- is fully
    stripped. The first intent found is the one that wins.
    """
    intent: Optional[str] = None

    for _ in range(3):
        for phrase, phrase_intent in INTENT_PHRASES:
            if f" {phrase} " in text:
                text = text.replace(f" {phrase} ", " ")
                intent = intent or phrase_intent
                break
        else:
            break

    if intent == "SHOW_OR_SEARCH":
        intent = _resolve_show(text)

    return intent, text


def _extract_price(text: str) -> Tuple[str, Optional[str]]:
    """Pull '300 से कम' style price limits out and return an English suffix."""
    for words, english in [(MAX_PRICE_WORDS, "under"), (MIN_PRICE_WORDS, "over")]:
        for word in words:
            pattern = rf"\s(\d+)\s+(?:रुपये|रुपए|रुपया|रु)?\s*{word}\s"
            match = re.search(pattern, text)
            if match:
                amount = match.group(1)
                text = text[: match.start()] + " " + text[match.end() :]
                return text, f"{english} {amount}"
    return text, None


def is_known_product(token: str) -> bool:
    """True when a token names a product, in Devanagari or as an ASR alias."""
    return token in PRODUCTS or token.lower() in ASR_ALIASES


def _translate_token(token: str) -> Optional[str]:
    """Map one Hindi token to English, or keep it if it is already usable."""
    lowered = token.lower()
    if token in FILLERS:
        return None
    if token in PRODUCTS:
        return PRODUCTS[token]
    # Latin-script mishearings are corrected before anything else is tried.
    if lowered in ASR_ALIASES:
        return ASR_ALIASES[lowered]
    if token in UNITS:
        return UNITS[token]
    if token in NUMBERS:
        return str(NUMBERS[token])
    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return token
    # Unknown Devanagari words are kept as-is: the item is then added as a
    # free-text entry rather than being silently dropped.
    return token


def to_english_command(text: str) -> str:
    """Rewrite a Hindi command as the equivalent canonical English command."""
    cleaned = _clean(text)
    intent, remainder = _detect_intent(cleaned)

    if intent in {"SHOW", "CLEAR", "RECOMMEND"}:
        return ENGLISH_VERBS[intent]

    remainder, price_suffix = _extract_price(remainder)

    words = [
        translated
        for translated in (_translate_token(token) for token in remainder.split())
        if translated
    ]

    if intent == "UPDATE":
        # "दूध की मात्रा 3 कर दो" -> tokens [milk, 3] -> "set milk to 3"
        numbers = [word for word in words if re.fullmatch(r"\d+(?:\.\d+)?", word)]
        item = " ".join(word for word in words if word not in numbers)
        if numbers and item:
            return f"set {item} to {numbers[-1]}"
        intent = None  # not enough information; fall through to a plain phrase

    body = " ".join(words).strip()
    if not body:
        return ENGLISH_VERBS.get(intent, "")

    if price_suffix:
        body = f"{body} {price_suffix}"

    verb = ENGLISH_VERBS.get(intent)
    if verb is None:
        # No recognised verb. A bare product name ("दूध") is treated as an add,
        # but a sentence with no known product word -- a greeting, small talk --
        # returns nothing so the parser reports it as not understood rather
        # than adding nonsense to the list.
        if not any(is_known_product(token) for token in remainder.split()):
            return ""
        verb = "add"
    return f"{verb} {body}"
