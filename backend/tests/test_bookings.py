"""Booking rules: confirmation paths, validation, ownership and concurrency."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from .conftest import CSRF, free_slot, login


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
