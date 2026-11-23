"""Shared fixtures: every test gets a fresh in-memory app with AI disabled."""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.ai.ai_service import AIService
from app.core.config import Settings
from app.main import create_app

CSRF = {"X-Requested-With": "LabLink"}


class FakeClient:
    """Test double for the Gemini client: returns or raises queued values and records calls."""

    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def generate(self, system: str, prompt: str, schema: type[BaseModel]) -> BaseModel:
        self.calls.append((system, prompt))
        response = self.responses.pop(0) if self.responses else RuntimeError("no response queued")
        if isinstance(response, Exception):
            raise response
        return schema.model_validate(response.model_dump() if isinstance(response, BaseModel) else response)


def make_client(**kwargs: Any) -> TestClient:
    settings = kwargs.pop("settings", Settings(ai_enabled=False))
    return TestClient(create_app(settings=settings, **kwargs), raise_server_exceptions=False)


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with make_client() as test_client:
        yield test_client


@pytest.fixture()
def client_factory() -> Callable[..., TestClient]:
    return make_client


@pytest.fixture()
def fake_ai() -> Callable[..., tuple[AIService, FakeClient]]:
    def build(*responses: Any) -> tuple[AIService, FakeClient]:
        fake = FakeClient(*responses)
        return AIService(fake), fake

    return build


def login(client: TestClient, persona: str) -> None:
    """Sign in as a seeded demo persona (clears any previous session)."""
    client.cookies.clear()
    response = client.post("/api/auth/demo", json={"persona_id": persona}, headers=CSRF)
    assert response.status_code == 200, response.text


def free_slot(client: TestClient, equipment_id: str) -> dict[str, str]:
    """Return the first free 30-minute slot for an equipment item."""
    days = client.get(f"/api/equipment/{equipment_id}/availability?days=5").json()["days"]
    return next(slot for day in days for slot in day["slots"] if slot["state"] == "free")
