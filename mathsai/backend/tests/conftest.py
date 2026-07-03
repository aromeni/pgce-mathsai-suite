"""Test fixtures.

Points DATABASE_URL at a throwaway file before any application module is
imported, so `database.engine` (bound at import time) never touches the
real dev database. Tests never call the real Anthropic API — ai_service
is always mocked (see test_ai_service.py / test_cache_service.py).
"""

import os

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_mathsai.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")

import pytest
from fastapi.testclient import TestClient

from database import Base, engine, get_db, SessionLocal
import main as main_module


@pytest.fixture(autouse=True)
def _reset_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    main_module.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main_module.app) as test_client:
        yield test_client
    main_module.app.dependency_overrides.clear()
