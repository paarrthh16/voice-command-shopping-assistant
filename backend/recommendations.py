"""Rule-based smart suggestions.

No model, no training, no external service: every recommendation is a sum of a
few named bonuses, and each bonus that fires contributes a reason string the UI
shows to the user. If a product is suggested, the screen says why.

    score = frequency + recency + category affinity
          + seasonal bonus + sale bonus + availability

Scoring is a pure function of data passed in (`score_products`), so the season
can be pinned in tests instead of depending on today's date.
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Sequence

import services
from models import Recommendation, RecommendationsResponse

# Simple season model. Month keys match the `season` column in the catalog,
# which stores comma-separated month abbreviations (or 'all').
SEASON_MONTHS: Dict[str, List[str]] = {
    "winter": ["dec", "jan", "feb"],
    "spring": ["mar", "apr"],
    "summer": ["may", "jun"],
    "monsoon": ["jul", "aug", "sep"],
    "autumn": ["oct", "nov"],
}

MONTH_KEYS = ["jan", "feb", "mar", "apr", "may", "jun",
              "jul", "aug", "sep", "oct", "nov", "dec"]

# Score weights, kept in one place so the formula is easy to read and tune.
FREQUENCY_WEIGHT = 2.0          # per past purchase, capped
FREQUENCY_CAP = 5               # purchases beyond this add nothing
RECENCY_RECENT = 3.0            # bought within a week
RECENCY_MEDIUM = 2.0            # within two weeks
RECENCY_OLD = 1.0               # within a month
CATEGORY_AFFINITY = 1.0         # same category as something bought before
SEASONAL_BONUS = 2.0
SALE_BONUS = 1.5
AVAILABLE_BONUS = 0.5
UNAVAILABLE_PENALTY = -3.0


@dataclass
class PurchaseStat:
    """One product's purchase history, already aggregated by the database."""

    name: str
    category: str
    purchases: int
    last_purchased: Optional[str] = None


@dataclass
class ScoredProduct:
    product: object
    score: float
    reasons: List[str]


def get_current_season(today: Optional[date] = None) -> str:
    """Return the season name for a date. Injectable so tests are deterministic."""
    today = today or datetime.now(timezone.utc).date()
    month_key = MONTH_KEYS[today.month - 1]
    for season, months in SEASON_MONTHS.items():
        if month_key in months:
            return season
    return "all"


def season_month_keys(season: str) -> List[str]:
    return SEASON_MONTHS.get(season, [])


def is_in_season(product_season: str, season: str) -> bool:
    """True when a product's months overlap the current season's months.

    Products marked 'all' are stocked year round; they get no seasonal bonus,
    otherwise every product would be 'seasonal' and the signal would be useless.
    """
    if not product_season or product_season.strip().lower() == "all":
        return False
    product_months = {month.strip().lower() for month in product_season.split(",")}
    return bool(product_months & set(season_month_keys(season)))


def _days_since(timestamp: Optional[str], now: Optional[datetime] = None) -> Optional[int]:
    if not timestamp:
        return None
    try:
        purchased_at = datetime.fromisoformat(timestamp)
    except ValueError:
        return None
    if purchased_at.tzinfo is None:
        purchased_at = purchased_at.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    return max(0, (now - purchased_at).days)


def score_products(
    products: Sequence,
    history: Sequence[PurchaseStat],
    season: str,
    excluded_names: Sequence[str] = (),
    now: Optional[datetime] = None,
) -> List[ScoredProduct]:
    """Score every catalog product. Pure: all inputs are passed in.

    Products already on the shopping list are skipped -- suggesting something
    the user has just added is noise.
    """
    stats_by_name = {stat.name.lower(): stat for stat in history}
    excluded = {name.lower() for name in excluded_names}

    # Categories the user actually buys from, used for a small affinity bonus.
    category_counts: Dict[str, int] = {}
    for stat in history:
        category_counts[stat.category] = category_counts.get(stat.category, 0) + stat.purchases
    favourite_categories = {
        category
        for category, _ in sorted(category_counts.items(), key=lambda pair: -pair[1])[:2]
    }

    scored: List[ScoredProduct] = []

    for product in products:
        if product.name.lower() in excluded:
            continue

        score = 0.0
        reasons: List[str] = []
        stat = stats_by_name.get(product.name.lower())

        if stat:
            score += min(stat.purchases, FREQUENCY_CAP) * FREQUENCY_WEIGHT
            reasons.append(
                "Frequently purchased" if stat.purchases > 1 else "You bought this before"
            )

            days = _days_since(stat.last_purchased, now)
            if days is not None:
                if days <= 7:
                    score += RECENCY_RECENT
                    reasons.append("Based on your recent purchases")
                elif days <= 14:
                    score += RECENCY_MEDIUM
                elif days <= 30:
                    score += RECENCY_OLD
                    reasons.append("You may be running low")
        elif product.category in favourite_categories:
            score += CATEGORY_AFFINITY
            reasons.append(f"You often buy {product.category}")

        if is_in_season(product.season, season):
            score += SEASONAL_BONUS
            reasons.append(f"In season now ({season})")

        if product.on_sale:
            score += SALE_BONUS
            reasons.append("On sale")

        score += AVAILABLE_BONUS if product.available else UNAVAILABLE_PENALTY
        if not product.available:
            reasons.append("Currently unavailable")

        if score > 0 and reasons:
            scored.append(ScoredProduct(product=product, score=round(score, 2), reasons=reasons))

    # Sort by score, then price, then name so the order never wobbles between
    # identical runs.
    scored.sort(key=lambda entry: (-entry.score, entry.product.price, entry.product.name))
    return scored


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def build_recommendations(limit: int = 6, today: Optional[date] = None) -> RecommendationsResponse:
    """Read the catalog, history and current list, then score and rank.

    Three queries in total, regardless of catalog size.
    """
    season = get_current_season(today)
    products = services.list_products()
    history_rows = services.purchase_history_summary()
    on_list = [item.name for item in services.get_shopping_list() if not item.completed]

    history = [
        PurchaseStat(
            name=row["name"],
            category=row["category"] or "Other",
            purchases=row["purchases"],
            last_purchased=row["last_purchased"],
        )
        for row in history_rows
    ]

    scored = score_products(products, history, season, excluded_names=on_list)[:limit]

    if history:
        message = "Suggestions based on your purchase history, the season and current offers."
    else:
        message = "No purchase history yet. Here are seasonal picks and current offers."

    return RecommendationsResponse(
        season=season,
        has_history=bool(history),
        message=message,
        recommendations=[
            Recommendation(product=entry.product, score=entry.score, reasons=entry.reasons)
            for entry in scored
        ],
    )
