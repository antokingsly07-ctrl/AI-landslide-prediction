"""Shared pytest fixtures.

Sets up DATABASE_URL to a temp SQLite file BEFORE the app module is imported
so all tests run against an isolated, disposable database.
"""
import os
import pathlib
import tempfile

_TMP = tempfile.TemporaryDirectory()
_DB_PATH = pathlib.Path(_TMP.name) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["ENVIRONMENT"] = "testing"

import sys  # noqa: E402

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.session import Base, engine, SessionLocal, init_db  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    """Create a fresh user and return Authorization headers."""
    import uuid

    email = f"tester_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Test User",
        "phone": "5550000000",
        "password": "testpass123",
        "district_id": None,
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}