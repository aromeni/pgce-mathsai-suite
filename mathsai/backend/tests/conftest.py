"""Test fixtures.

Points DATABASE_URL at a throwaway file before any application module is
imported, so `database.engine` (bound at import time) never touches the
real dev database. Tests never call the real Anthropic API — ai_service
is always mocked (see test_ai_service.py / test_cache_service.py).

Authentication is switched ON for the whole suite rather than bypassed, so
every existing route test exercises the same configuration that runs in
production; the `client` fixture simply logs in first. `anon_client` is the
deliberately unauthenticated counterpart used by test_auth.py.
"""

import os

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_mathsai.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")

import pytest
from fastapi.testclient import TestClient

import auth

TEST_PASSWORD = "correct-horse-battery-staple"
os.environ["APP_PASSWORD_HASH"] = auth.hash_password(TEST_PASSWORD)
os.environ["SECRET_KEY"] = "test-secret-key-not-used-outside-tests"

from database import Base, engine, get_db, SessionLocal
import main as main_module


@pytest.fixture(autouse=True)
def _reset_login_throttle():
    """The attempt counter is module-level state; keep tests independent."""
    auth.reset_rate_limits()
    yield
    auth.reset_rate_limits()


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
def anon_client(db_session):
    """A client that has not logged in."""

    def override_get_db():
        yield db_session

    main_module.app.dependency_overrides[get_db] = override_get_db
    # follow_redirects=False so tests can assert on the 303 to /login rather
    # than silently following it and seeing a 200.
    with TestClient(main_module.app, follow_redirects=False) as test_client:
        yield test_client
    main_module.app.dependency_overrides.clear()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    main_module.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main_module.app) as test_client:
        response = test_client.post(
            "/api/auth/login", json={"password": TEST_PASSWORD}
        )
        assert response.status_code == 200, "test login failed — fixture is broken"
        yield test_client
    main_module.app.dependency_overrides.clear()
