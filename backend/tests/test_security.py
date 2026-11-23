"""Security controls: headers, CSRF, input limits, production hardening, error hygiene."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings

from .conftest import CSRF, login

PROD = Settings(production=True, session_secret="s" * 48, ai_enabled=False)


def test_api_responses_are_not_cached(client: TestClient) -> None:
    assert "no-store" in client.get("/api/healthz").headers.get("cache-control", "")


def test_unknown_fields_rejected(client: TestClient) -> None:
    login(client, "u-aarav")
    response = client.post("/api/ai/search", json={"query": "scope", "admin": True}, headers=CSRF)
    assert response.status_code == 422


def test_oversized_body_rejected(client: TestClient) -> None:
    login(client, "u-aarav")
    response = client.post("/api/ai/search", content="x" * 70_000, headers={**CSRF, "Content-Type": "application/json"})
    assert response.status_code == 413


def test_production_hardening(client_factory) -> None:
    with client_factory(settings=PROD) as client:
        assert client.get("/api/docs").status_code == 404
        assert "strict-transport-security" in client.get("/api/healthz").headers
        response = client.post("/api/auth/demo", json={"persona_id": "u-aarav"}, headers=CSRF)
        assert "secure" in response.headers["set-cookie"].lower()


def test_unexpected_errors_are_generic(client_factory) -> None:
    with client_factory() as client:
        login(client, "u-aarav")

        def boom() -> None:
            raise RuntimeError("database exploded with secret details")

        client.app.state.repo.read = boom
        response = client.get("/api/bookings/mine")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["request_id"]
    assert "secret details" not in response.text


def test_spa_routes_and_asset_caching(client_factory, tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>LabLink</title>")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    with client_factory(static_dir=tmp_path) as client:
        page = client.get("/discover")
        asset = client.get("/assets/app.js")
        missing = client.get("/api/unknown")
    assert page.status_code == 200
    assert page.headers["cache-control"] == "no-cache"
    assert "immutable" in asset.headers["cache-control"]
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
