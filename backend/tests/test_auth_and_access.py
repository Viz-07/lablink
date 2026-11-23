"""Authentication and role-based authorisation tests."""

import pytest
from fastapi.testclient import TestClient

from .conftest import CSRF, login


def test_personas_listed(client: TestClient) -> None:
    personas = client.get("/api/auth/personas").json()
    assert len(personas) == 7
    assert {p["role"] for p in personas} == {"student", "faculty", "lab_admin"}


def test_session_cookie_flags_and_me(client: TestClient) -> None:
    response = client.post("/api/auth/demo", json={"persona_id": "u-aarav"}, headers=CSRF)
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert client.get("/api/auth/me").json()["user"]["id"] == "u-aarav"


def test_unknown_persona_and_anonymous_access(client: TestClient) -> None:
    assert client.post("/api/auth/demo", json={"persona_id": "u-nobody"}, headers=CSRF).status_code in {404, 422}
    assert client.get("/api/bookings/mine").status_code == 401


def test_tampered_cookie_is_rejected(client: TestClient) -> None:
    login(client, "u-aarav")
    token = client.cookies.get("ll_session")
    client.cookies.clear()
    client.cookies.set("ll_session", token[:-3] + ("AAA" if not token.endswith("AAA") else "BBB"))
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_session(client: TestClient) -> None:
    login(client, "u-aarav")
    assert client.post("/api/auth/logout", headers=CSRF).status_code == 204
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401


ROUTES = [
    ("GET", "/api/approvals"),
    ("GET", "/api/conflicts"),
    ("GET", "/api/analytics/overview?range_days=7"),
    ("GET", "/api/admin/equipment"),
    ("GET", "/api/admin/audit"),
]
EXPECTED = {
    "u-aarav": [403, 403, 403, 403, 403],
    "u-meera": [200, 200, 200, 403, 403],
    "u-ravi": [200, 200, 200, 200, 200],
}


@pytest.mark.parametrize("persona", list(EXPECTED))
def test_authorization_matrix(client: TestClient, persona: str) -> None:
    login(client, persona)
    statuses = [client.request(method, path).status_code for method, path in ROUTES]
    assert statuses == EXPECTED[persona]


@pytest.mark.parametrize("persona", ["u-aarav", "u-meera"])
def test_only_admin_can_reset_demo(client: TestClient, persona: str) -> None:
    login(client, persona)
    assert client.post("/api/admin/demo/reset", headers=CSRF).status_code == 403


def test_admin_reset_reseeds_demo(client: TestClient) -> None:
    login(client, "u-meera")
    client.post("/api/conflicts/cf-demo-spectrum/recommend", headers=CSRF)
    client.post("/api/conflicts/cf-demo-spectrum/apply", json={}, headers=CSRF)
    login(client, "u-ravi")
    assert client.post("/api/admin/demo/reset", headers=CSRF).json() == {"reset": True}
    open_ids = [c["id"] for c in client.get("/api/conflicts?status=open").json()]
    assert "cf-demo-spectrum" in open_ids
