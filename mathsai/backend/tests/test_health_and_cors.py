"""Phase 8 — /api/health and CORS configuration (CLAUDE.md CORS and health
checks: "CORS ... allows only the known frontend origin(s) — never *").
FRONTEND_ORIGIN defaults to http://localhost:5173 (conftest.py doesn't
override it), which is what these tests check against."""


def test_health_returns_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_configured_frontend_origin(client):
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_other_origin(client):
    response = client.get("/api/health", headers={"Origin": "http://evil.example.com"})
    assert response.headers.get("access-control-allow-origin") != "http://evil.example.com"
    assert "access-control-allow-origin" not in response.headers
