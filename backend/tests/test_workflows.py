"""Conflicts, approvals, projects, analytics, notifications and admin workflows."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from .conftest import CSRF, login


def test_both_demo_conflicts_are_open(client: TestClient) -> None:
    login(client, "u-ravi")
    ids = {c["id"] for c in client.get("/api/conflicts?status=open").json()}
    assert {"cf-demo-spectrum", "cf-demo-gpu"} <= ids
    assert client.get("/api/conflicts/cf-demo-gpu").json()["capacity"] >= 1


def test_student_cannot_resolve_conflicts(client: TestClient) -> None:
    login(client, "u-aarav")
    assert client.post("/api/conflicts/cf-demo-spectrum/recommend", headers=CSRF).status_code == 403
    assert client.post("/api/conflicts/cf-demo-spectrum/apply", json={}, headers=CSRF).status_code == 403


def test_loser_accepts_alternative(client: TestClient) -> None:
    login(client, "u-meera")
    client.post("/api/conflicts/cf-demo-spectrum/recommend", headers=CSRF)
    client.post("/api/conflicts/cf-demo-spectrum/apply", json={}, headers=CSRF)
    login(client, "u-sneha")
    booking = client.get("/api/bookings/mine?when=action").json()["items"][0]
    accepted = client.post(f"/api/bookings/{booking['id']}/accept-alternative", json={"index": 0}, headers=CSRF)
    assert accepted.status_code == 201
    assert accepted.json()["status"] in {"confirmed", "pending_approval"}
    assert client.get("/api/notifications").json()["items"]


def test_faculty_sees_only_their_items(client: TestClient) -> None:
    login(client, "u-arjun")
    names = [name for item in client.get("/api/approvals").json() for name in item["equipment"]]
    assert names
    assert "Keysight N9320B Spectrum Analyser" not in names


def test_decline_requires_comment(client: TestClient) -> None:
    login(client, "u-arjun")
    item = next(i for i in client.get("/api/approvals").json() if i["type"] == "access")
    url = f"/api/approvals/access/{item['id']}/decline"
    assert client.post(url, json={"comment": ""}, headers=CSRF).status_code == 422


def test_approving_access_creates_grant(client: TestClient) -> None:
    login(client, "u-arjun")
    item = next(i for i in client.get("/api/approvals").json() if i["type"] == "access")
    summary = client.get(f"/api/approvals/access/{item['id']}/summary").json()
    assert summary["source"] == "fallback"
    approved = client.post(f"/api/approvals/access/{item['id']}/approve", json={"comment": "Approved"}, headers=CSRF)
    assert approved.status_code == 200
    login(client, "u-diya")
    assert client.get("/api/access-grants/mine").json()


def test_project_and_access_request_lifecycle(client: TestClient) -> None:
    login(client, "u-kabir")
    past = {
        "title": "Old idea",
        "description": "A project whose deadline is already over.",
        "type": "personal",
        "deadline": str(date.today() - timedelta(days=3)),
    }
    assert client.post("/api/projects", json=past, headers=CSRF).status_code == 422
    project = client.post(
        "/api/projects", json={**past, "deadline": str(date.today() + timedelta(days=10))}, headers=CSRF
    )
    assert project.status_code == 201
    request = {
        "project_id": project.json()["id"],
        "equipment_ids": ["eq-prusa"],
        "hours_requested": 4,
        "needed_from": str(date.today() + timedelta(days=1)),
        "needed_until": str(date.today() + timedelta(days=9)),
        "justification": "I need to print and compare three frame designs before the deadline.",
    }
    created = client.post("/api/access-requests", json=request, headers=CSRF)
    assert created.status_code == 201
    withdrawn = client.post(f"/api/access-requests/{created.json()['id']}/withdraw", headers=CSRF)
    assert withdrawn.status_code == 200
    assert client.get("/api/access-requests/mine").status_code == 200


def test_analytics_overview_shape(client: TestClient) -> None:
    login(client, "u-ravi")
    data = client.get("/api/analytics/overview?range_days=30").json()
    assert {"kpis", "by_equipment", "heatmap"} <= data.keys()
    assert data["kpis"]["bookings"] > 0
    insights = client.post("/api/ai/insights", json={"range_days": 30}, headers=CSRF).json()
    assert insights["source"] == "fallback"
    assert insights["insights"]


def test_notifications_mark_read(client: TestClient) -> None:
    login(client, "u-aarav")
    assert client.get("/api/notifications/unread-count").json()["unread_count"] >= 1
    assert client.post("/api/notifications/read", json={"ids": "all"}, headers=CSRF).status_code == 204
    assert client.get("/api/notifications/unread-count").json()["unread_count"] == 0


def test_admin_equipment_and_certifications(client: TestClient) -> None:
    login(client, "u-ravi")
    created = client.post(
        "/api/admin/equipment",
        headers=CSRF,
        json={
            "name": "Thermal Camera",
            "lab_id": "lab-makerspace",
            "category": "measurement",
            "description": "Handheld thermal imaging camera.",
            "specs": {"Resolution": "320x240"},
            "capability_tags": ["thermal", "imaging"],
            "units": 2,
        },
    )
    assert created.status_code == 201
    edited = client.patch(f"/api/admin/equipment/{created.json()['id']}", json={"status": "maintenance"}, headers=CSRF)
    assert edited.status_code == 200
    certs = client.post("/api/admin/users/u-kabir/certifications", json={"add": ["laser-safety"]}, headers=CSRF)
    assert "laser-safety" in certs.json()["certifications"]
    assert client.get("/api/admin/audit").json()["items"]
