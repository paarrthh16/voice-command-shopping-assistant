"""Pydantic request/response models for the API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: int
    name: str
    category: str
    brand: str = ""
    size: str = ""
    unit: str = "piece"
    price: float = 0
    available: bool = True
    season: str = "all"
    on_sale: bool = False
    substitutes: List[str] = []


class ShoppingListItem(BaseModel):
    id: int
    product_id: Optional[int] = None
    name: str
    category: str
    quantity: float
    unit: str
    completed: bool
    created_at: str
    updated_at: str


class ShoppingListItemCreate(BaseModel):
    """Add an item either by catalog product id or by free-text name."""

    product_id: Optional[int] = None
    name: Optional[str] = Field(default=None, max_length=100)
    quantity: float = Field(default=1, gt=0, le=999)
    unit: Optional[str] = Field(default=None, max_length=20)
    category: Optional[str] = Field(default=None, max_length=50)


class ShoppingListItemUpdate(BaseModel):
    """Partial update. Every field is optional; at least one must be supplied."""

    quantity: Optional[float] = Field(default=None, gt=0, le=999)
    unit: Optional[str] = Field(default=None, max_length=20)
    completed: Optional[bool] = None


class CommandRequest(BaseModel):
    """A voice transcript or a typed command."""

    text: str = Field(min_length=1, max_length=200)


class SearchFilters(BaseModel):
    """Filters understood from a search command, echoed back for the UI."""

    query: Optional[str] = None
    brand: Optional[str] = None
    size: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None


class Recommendation(BaseModel):
    """A suggested product with its score and the reasons behind it."""

    product: Product
    score: float
    reasons: List[str] = []


class RecommendationsResponse(BaseModel):
    season: str
    has_history: bool
    message: str
    recommendations: List[Recommendation] = []


class SubstituteGroup(BaseModel):
    """Alternatives offered for one product, used for unavailable items."""

    for_product: str
    alternatives: List[Product] = []


class CommandResponse(BaseModel):
    """What the assistant understood, what it did, and the resulting list."""

    transcript: str
    intent: str
    language: str = "en"
    # For a Hindi command, the English command it was rewritten to.
    understood_as: Optional[str] = None
    item: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    matched_product: Optional[str] = None
    success: bool
    message: str
    items: List[ShoppingListItem] = []
    filters: Optional[SearchFilters] = None
    results: List[Product] = []
    substitutes: List[SubstituteGroup] = []
    recommendations: List[Recommendation] = []


class HealthResponse(BaseModel):
    status: str
    database: str
    product_count: int
