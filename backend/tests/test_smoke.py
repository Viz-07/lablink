"""End-to-end smoke tests for the LabLink API (in-memory storage, AI fallback)."""

from fastapi.testclient import TestClient

from .conftest import CSRF, free_slot, login


def test_health(client: TestClient) -> None:
    body = client.get("/api/healthz").json()
    assert body["status"] == "ok"
    assert body["storage"] == "memory"
    assert body["model"]


def test_security_headers(client: TestClient) -> None:
    headers = client.get("/api/healthz").headers
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert headers["x-content-type-options"] == "nosniff"


def test_post_without_csrf_header_is_rejected(client: TestClient) -> None:
    assert client.post("/api/auth/demo", json={"persona_id": "u-aarav"}).status_code == 403


def test_student_cannot_open_faculty_pages(client: TestClient) -> None:
    login(client, "u-aarav")
    assert client.get("/api/approvals").status_code == 403
    assert client.get("/api/analytics/overview?range_days=7").status_code == 403


def test_catalogue_and_search(client: TestClient) -> None:
    login(client, "u-aarav")
    assert client.get("/api/equipment?limit=5").json()["total"] == 40
    hits = client.post("/api/ai/search", json={"query": "measure 2.4 GHz antenna signals"}, headers=CSRF).json()
    assert hits["results"][0]["equipment_id"] == "eq-spectrum-keysight"


def test_invalid_booking_input_is_rejected(client: TestClient) -> None:
    login(client, "u-diya")
    slot = free_slot(client, "eq-spectrum-rs")
    body = {"equipment_id": "eq-spectrum-rs", "start": slot["start"], "end": slot["end"], "purpose": "x"}
    assert client.post("/api/bookings", json=body, headers=CSRF).status_code == 422


def test_book_and_cancel(client: TestClient) -> None:
    login(client, "u-diya")
    slot = free_slot(client, "eq-spectrum-rs")
    body = {
        "equipment_id": "eq-spectrum-rs",
        "start": slot["start"],
        "end": slot["end"],
        "purpose": "Prototype test run",
    }
    booking = client.post("/api/bookings", json=body, headers=CSRF)
    assert booking.status_code == 201
    assert booking.json()["status"] == "confirmed"
    assert client.post(f"/api/bookings/{booking.json()['id']}/cancel", json={}, headers=CSRF).status_code == 200


def test_fair_allocation_resolves_demo_conflict(client: TestClient) -> None:
    login(client, "u-meera")
    ranking = client.post("/api/conflicts/cf-demo-spectrum/recommend", headers=CSRF).json()["recommendation"]
    assert ranking[0]["student"] == "Aarav Shetty"
    assert ranking[0]["unit_id"]
    assert all(row["reason"] == "CAPACITY" and len(row["alternatives"]) == 3 for row in ranking[1:])
    assert client.post("/api/conflicts/cf-demo-spectrum/apply", json={}, headers=CSRF).json()["status"] == "resolved"
    assert client.post("/api/conflicts/cf-demo-spectrum/apply", json={}, headers=CSRF).status_code == 409


def test_loser_receives_alternatives(client: TestClient) -> None:
    login(client, "u-meera")
    client.post("/api/conflicts/cf-demo-spectrum/recommend", headers=CSRF)
    client.post("/api/conflicts/cf-demo-spectrum/apply", json={}, headers=CSRF)
    login(client, "u-sneha")
    items = client.get("/api/bookings/mine?when=action").json()["items"]
    assert items[0]["status"] == "reallocated"
    assert len(items[0]["alternatives"]) == 3
