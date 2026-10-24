import os
import sys
from collections.abc import Generator
from pathlib import Path

os.environ.setdefault("PSEUDOGRAM_API_KEY", "test-secret-key")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import database as app_database  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
import app.models  # noqa: E402, F401

TEST_API_KEY = "test-secret-key"


@pytest.fixture(autouse=True)
def configure_test_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PSEUDOGRAM_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def db_engine():
    # StaticPool keeps a single in-memory SQLite database across connections.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Rebind the app's global engine/session to the test DB before schema creation.
    app_database.engine = engine
    app_database.SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    app_database.Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Generator[Session, None, None]:
    session = app_database.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = app_database.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[app_database.get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
