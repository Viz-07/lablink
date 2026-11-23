"""Booking rules: confirmation paths, validation, ownership and concurrency."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.clock import FixedClock
from app.domain.timeslots import at_local

from .conftest import CSRF, free_slot, login, make_client


def body(slot: dict[str, str], equipment: str = "eq-spectrum-rs", **extra: object) -> dict[str, object]:
    return {
        "equipment_id": equipment,
        "start": slot["start"],
        "end": slot["end"],
        "purpose": "Lab measurements",
        **extra,
    }


def shifted(value: str, minutes: int) -> str:
    return (datetime.fromisoformat(value.replace("Z", "+00:00")) + timedelta(minutes=minutes)).isoformat()


def test_full_slot_returns_409_with_alternatives(client: TestClient) -> None:
    login(client, "u-diya")
    slot = free_slot(client, "eq-spectrum-rs")
    assert client.post("/api/bookings", json=body(slot), headers=CSRF).status_code == 201
    login(client, "u-kabir")
    response = client.post("/api/bookings", json=body(slot), headers=CSRF)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SLOT_UNAVAILABLE"


def test_faculty_mode_equipment_needs_review(client: TestClient) -> None:
    login(client, "u-diya")
    slot = free_slot(client, "eq-gpu-4090")
    response = client.post("/api/bookings", json=body(slot, "eq-gpu-4090", project_id="pr-diya"), headers=CSRF)
    assert response.status_code == 201
    assert response.json()["status"] in {"pending_approval", "contested", "confirmed"}


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: {**s, "start": shifted(s["start"], 10)},
        lambda s: {**s, "end": s["start"]},
        lambda s: {**s, "end": shifted(s["start"], 600)},
    ],
    ids=["misaligned", "zero-length", "too-long"],
)
def test_invalid_intervals_rejected(client: TestClient, mutate) -> None:
    login(client, "u-diya")
    slot = mutate(free_slot(client, "eq-spectrum-rs"))
    assert client.post("/api/bookings", json=body(slot), headers=CSRF).status_code == 422


def test_past_booking_rejected(client: TestClient) -> None:
    login(client, "u-diya")
    slot = free_slot(client, "eq-spectrum-rs")
    past = {"start": shifted(slot["start"], -60 * 24 * 7), "end": shifted(slot["end"], -60 * 24 * 7)}
    assert client.post("/api/bookings", json=body(past), headers=CSRF).status_code in {409, 422}


def test_cannot_cancel_or_view_someone_elses_booking(client: TestClient) -> None:
    login(client, "u-diya")
    booking = client.post("/api/bookings", json=body(free_slot(client, "eq-spectrum-rs")), headers=CSRF).json()
    login(client, "u-kabir")
    assert client.get(f"/api/bookings/{booking['id']}").status_code == 403
    assert client.post(f"/api/bookings/{booking['id']}/cancel", json={}, headers=CSRF).status_code == 403


def test_concurrent_booking_of_last_unit(client: TestClient) -> None:
    login(client, "u-diya")
    slot = free_slot(client, "eq-spectrum-rs")
    with TestClient(client.app) as second:
        login(second, "u-kabir")

        def attempt(c: TestClient) -> int:
            return c.post("/api/bookings", json=body(slot), headers=CSRF).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = sorted(pool.map(attempt, [client, second]))
    assert codes == [201, 409]


def test_my_bookings_tabs(client: TestClient) -> None:
    login(client, "u-diya")
    for when in ("upcoming", "past", "action"):
        assert client.get(f"/api/bookings/mine?when={when}").status_code == 200


def test_booking_calendar_and_suggestions_obey_horizon() -> None:
    with make_client(clock=FixedClock(at_local(date(2026, 11, 23), "10:15"))) as client:
        login(client, "u-diya")
        equipment = "/api/equipment/eq-spectrum-rs"
        horizon_day = "2026-12-07"
        calendar = client.get(f"{equipment}/availability", params={"from": horizon_day, "days": 2}).json()
        boundary = at_local(date.fromisoformat(horizon_day), "10:15")
        slots = [slot for day in calendar["days"] for slot in day["slots"]]
        assert any(slot["state"] == "free" for slot in slots)
        assert all(
            slot["state"] == "outside_horizon" and slot["free_units"] == 0
            for slot in slots
            if datetime.fromisoformat(slot["end"]) > boundary
        )
        suggestions = client.get(
            f"{equipment}/suggest-slots",
            params={"earliest": horizon_day, "latest": "9999-12-31", "duration_minutes": 30},
        ).json()["suggestions"]
        assert suggestions and all(datetime.fromisoformat(slot["end"]) <= boundary for slot in suggestions)
        assert client.get(f"{equipment}/suggest-slots", params={"earliest": "9999-12-31"}).json() == {"suggestions": []}


def test_catalogue_handles_dates_beyond_horizon_and_invalid_cursor(client: TestClient) -> None:
    login(client, "u-diya")
    assert client.get("/api/equipment", params={"available_on": "9999-12-31"}).json()["total"] == 0
    for url in ("/api/equipment", "/api/bookings/mine"):
        invalid = client.get(url, params={"cursor": "ll-\u00b2"})
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "BAD_CURSOR"
        assert client.get(url, params={"cursor": "ll-0", "limit": 1}).status_code == 200
