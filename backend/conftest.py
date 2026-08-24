"""Shared pytest fixtures.

Living at the backend root (not inside tests/) makes pytest add this
directory to sys.path, so test modules can `import nlp`, `import services`,
etc. exactly like the application code does.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import database  # noqa: E402


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Point the app at a fresh, empty SQLite file for one test.

    Every test gets its own database, seeded with the real catalog, so tests
    never depend on execution order or leak state into each other.
    """
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    yield database.DB_PATH


@pytest.fixture()
def client(db):
    """A FastAPI TestClient wired to the isolated test database."""
    from fastapi.testclient import TestClient

    import main

    with TestClient(main.app) as test_client:
        yield test_client
