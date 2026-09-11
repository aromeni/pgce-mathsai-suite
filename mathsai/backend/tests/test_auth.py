"""Authentication tests.

The gate exists to stop an anonymous visitor spending Anthropic credits via
the regenerate routes, so the cases that matter are: unauthenticated access
is refused everywhere it should be, the health probe still works, and a
production misconfiguration cannot boot.
"""

import importlib
import os
from unittest.mock import patch

import pytest

import auth
from conftest import TEST_PASSWORD


def test_health_is_reachable_without_login(anon_client):
    """The platform health probe has no session and must not be redirected."""
    response = anon_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_page_is_reachable_without_login(anon_client):
    response = anon_client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/topics",
        "/api/lessons/1",
        "/api/questions/1/Foundation",
        "/api/progress",
        "/api/export/lesson/1/pdf",
    ],
)
def test_api_routes_require_authentication(anon_client, path):
    response = anon_client.get(path)
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_regenerate_routes_require_authentication(anon_client):
    """The specific routes that cost money on a single request."""
    assert anon_client.post("/api/lessons/1/refresh").status_code == 401
    assert (
        anon_client.post("/api/questions/1/Foundation/refresh").status_code == 401
    )


@pytest.mark.parametrize("path", ["/", "/lesson/1", "/progress"])
def test_page_routes_redirect_to_login(anon_client, path):
    response = anon_client.get(path)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_frontend_bundle_is_not_served_to_anonymous_visitors(anon_client):
    """An unauthenticated visitor should not even receive the SPA assets."""
    response = anon_client.get("/assets/index.js")
    assert response.status_code == 303


def test_login_with_correct_password_sets_session(anon_client):
    response = anon_client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    assert response.status_code == 200
    assert auth.SESSION_COOKIE in response.cookies
    assert anon_client.get("/api/topics").status_code == 200


def test_login_with_wrong_password_is_rejected(anon_client):
    response = anon_client.post("/api/auth/login", json={"password": "wrong"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect password."
    assert anon_client.get("/api/topics").status_code == 401


def test_logout_clears_the_session(client):
    assert client.get("/api/topics").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/topics").status_code == 401


def test_repeated_failures_are_rate_limited(anon_client):
    for _ in range(auth.MAX_ATTEMPTS):
        assert (
            anon_client.post("/api/auth/login", json={"password": "wrong"}).status_code
            == 401
        )

    blocked = anon_client.post("/api/auth/login", json={"password": "wrong"})
    assert blocked.status_code == 429

    # The correct password is refused too while the window is open — the
    # limiter gates the endpoint, not just bad guesses.
    assert (
        anon_client.post(
            "/api/auth/login", json={"password": TEST_PASSWORD}
        ).status_code
        == 429
    )


def test_successful_login_clears_the_failure_count(anon_client):
    for _ in range(auth.MAX_ATTEMPTS - 1):
        anon_client.post("/api/auth/login", json={"password": "wrong"})

    assert (
        anon_client.post(
            "/api/auth/login", json={"password": TEST_PASSWORD}
        ).status_code
        == 200
    )

    anon_client.post("/api/auth/logout")
    # Counter was reset by the success, so a fresh run of failures is allowed.
    assert (
        anon_client.post("/api/auth/login", json={"password": "wrong"}).status_code
        == 401
    )


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------

def test_hash_is_salted_and_verifiable():
    first = auth.hash_password("a-long-enough-password")
    second = auth.hash_password("a-long-enough-password")
    assert first != second, "each hash must use a fresh salt"
    assert auth.verify_password("a-long-enough-password", first)
    assert auth.verify_password("a-long-enough-password", second)
    assert not auth.verify_password("a-long-enough-passwore", first)


@pytest.mark.parametrize(
    "corrupt",
    ["", "not-a-hash", "scrypt$16384$8$1$badbase64", "bcrypt$16384$8$1$AA==$AA=="],
)
def test_malformed_hash_denies_access_rather_than_raising(corrupt):
    """A truncated or corrupted APP_PASSWORD_HASH must fail closed, not 500."""
    assert auth.verify_password("anything", corrupt) is False


# --------------------------------------------------------------------------
# Fail-closed production configuration
# --------------------------------------------------------------------------

def test_production_without_password_hash_refuses_to_start():
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "APP_PASSWORD_HASH": ""}):
        with pytest.raises(RuntimeError, match="APP_PASSWORD_HASH"):
            auth.check_auth_config()


def test_production_without_secret_key_refuses_to_start():
    with patch.dict(
        os.environ,
        {"ENVIRONMENT": "production", "APP_PASSWORD_HASH": "x", "SECRET_KEY": ""},
    ):
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            auth.check_auth_config()


def test_fully_configured_production_starts():
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "APP_PASSWORD_HASH": "x",
            "SECRET_KEY": "y",
        },
    ):
        auth.check_auth_config()


def test_development_without_password_hash_is_allowed():
    """Local dev stays frictionless; only production is forced closed."""
    with patch.dict(os.environ, {"ENVIRONMENT": "development", "APP_PASSWORD_HASH": ""}):
        auth.check_auth_config()
        assert auth.auth_enabled() is False
