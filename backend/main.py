"""Voice Command Shopping Assistant - API.

Serves the product catalog, the shopping list, and the command endpoint that
voice and typed input share. Speech capture happens in the browser; this API
receives the transcript as text.
"""

import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path as FilePath
from typing import List, Optional

import commands
import recommendations
import services
from database import init_db
from fastapi import FastAPI, Path, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from models import (
    CommandRequest,
    CommandResponse,
    HealthResponse,
    Product,
    RecommendationsResponse,
    ShoppingListItem,
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
)
from services import ServiceError


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Voice Command Shopping Assistant API",
    version="0.1.0",
    lifespan=lifespan,
)

# The Vite dev server runs on a different port during development. Deployments
# that serve the frontend from another origin can pass a comma-separated
# ALLOWED_ORIGINS environment variable instead of editing this file.
DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQLite stores row ids as signed 64-bit integers; anything larger cannot be
# bound as a query parameter, so ids are bounded at the edge.
MAX_ROW_ID = 2**63 - 1
ProductId = Path(ge=1, le=MAX_ROW_ID, description="Catalog product id")
ItemId = Path(ge=1, le=MAX_ROW_ID, description="Shopping list item id")


# --------------------------------------------------------------------------- #
# Error handling
# --------------------------------------------------------------------------- #

@app.exception_handler(ServiceError)
async def handle_service_error(request: Request, error: ServiceError):
    return JSONResponse(status_code=error.status_code, content={"detail": error.message})


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, error: RequestValidationError):
    """Flatten FastAPI's validation output into a single readable sentence."""
    first = error.errors()[0]
    field = ".".join(str(part) for part in first["loc"] if part != "body") or "request"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": f"Invalid value for '{field}': {first['msg']}"},
    )


@app.exception_handler(sqlite3.Error)
async def handle_database_error(request: Request, error: sqlite3.Error):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error. Please try again."},
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, error: Exception):
    """Last resort: answer with JSON the frontend can display, never a bare 500."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Something went wrong. Please try again."},
    )


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #

@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", database="connected", product_count=services.count_products())


# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #

@app.get("/api/products", response_model=List[Product])
def get_products(
    search: Optional[str] = Query(default=None, max_length=100),
    category: Optional[str] = Query(default=None, max_length=50),
):
    return services.list_products(search=search, category=category)


@app.get("/api/products/search", response_model=List[Product])
def search_products(
    query: Optional[str] = Query(default=None, max_length=100),
    brand: Optional[str] = Query(default=None, max_length=50),
    size: Optional[str] = Query(default=None, max_length=20),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    category: Optional[str] = Query(default=None, max_length=50),
    limit: int = Query(default=20, ge=1, le=50),
):
    """Filtered catalog search. Declared before /api/products/{product_id} so
    that the literal path 'search' is not read as a product id."""
    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price
    return services.search_products(
        query=query,
        brand=brand,
        size=size,
        min_price=min_price,
        max_price=max_price,
        category=category,
        limit=limit,
    )


@app.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: int = ProductId):
    return services.get_product(product_id)


@app.get("/api/products/{product_id}/substitutes", response_model=List[Product])
def get_substitutes(product_id: int = ProductId):
    """Alternatives for a product, from the catalog's own substitutes field."""
    return services.get_substitutes(product_id)


@app.get("/api/recommendations", response_model=RecommendationsResponse)
def get_recommendations(limit: int = Query(default=6, ge=1, le=20)):
    return recommendations.build_recommendations(limit=limit)


@app.get("/api/categories", response_model=List[str])
def get_categories():
    return services.list_categories()


# --------------------------------------------------------------------------- #
# Shopping list
# --------------------------------------------------------------------------- #

@app.get("/api/shopping-list", response_model=List[ShoppingListItem])
def get_shopping_list():
    return services.get_shopping_list()


@app.post("/api/shopping-list", response_model=ShoppingListItem, status_code=status.HTTP_201_CREATED)
def create_shopping_list_item(payload: ShoppingListItemCreate):
    return services.add_item(payload)


@app.patch("/api/shopping-list/{item_id}", response_model=ShoppingListItem)
def patch_shopping_list_item(payload: ShoppingListItemUpdate, item_id: int = ItemId):
    return services.update_item(item_id, payload)


@app.delete("/api/shopping-list/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_shopping_list_item(item_id: int = ItemId):
    services.delete_item(item_id)
    return None


# --------------------------------------------------------------------------- #
# Voice / typed commands
# --------------------------------------------------------------------------- #

@app.post("/api/commands", response_model=CommandResponse)
def process_command(payload: CommandRequest):
    """Interpret a spoken or typed command and apply it to the shopping list.

    Voice and typed input share this single endpoint, so both go through the
    same parser and the same shopping-list services.
    """
    return commands.process_command(payload.text)


# --------------------------------------------------------------------------- #
# Production frontend
#
# In production the built React app is served from this same origin, which is
# why the frontend can call "/api/..." with no configured base URL and no CORS.
# These routes are registered last and only when a build is present, so local
# development (Vite on :5173 proxying to :8000) is unaffected.
# --------------------------------------------------------------------------- #

FRONTEND_DIST = FilePath(
    os.environ.get("FRONTEND_DIST", FilePath(__file__).resolve().parent.parent / "frontend" / "dist")
).resolve()

if FRONTEND_DIST.is_dir():
    assets = FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/", include_in_schema=False)
    def serve_index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        """Serve a built file when it exists, otherwise the SPA entry point.

        An unknown /api/* path must never fall through to the app shell, and a
        request may not escape the build directory.
        """
        if full_path.startswith("api/"):
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Not found"})

        candidate = (FRONTEND_DIST / full_path).resolve()
        if candidate.is_file() and FRONTEND_DIST in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
