"""Unit tests for the deterministic fair-allocation engine."""

from datetime import UTC, datetime, timedelta

from app.domain.models import Interval, PriorityBreakdown
from app.services.allocator import RequestInput, allocate

T0 = datetime(2026, 11, 24, 4, 30, tzinfo=UTC)


def request(
    key: str,
    score: float,
    *,
    user: str | None = None,
    start: int = 0,
    hours: int = 2,
    created: int = 0,
    reason: str | None = None,
) -> RequestInput:
    interval = Interval(start=T0 + timedelta(hours=start), end=T0 + timedelta(hours=start + hours))
    return RequestInput(
        id=key,
        user_id=user or f"u-{key}",
        interval=interval,
        created_at=T0 - timedelta(hours=created),
        priority=PriorityBreakdown(score=score, factors={}),
        reason=reason,
    )


def outcome(placements: list) -> dict[str, str | None]:
    return {p.request.id: p.unit_id for p in placements}


def test_highest_score_wins_single_unit() -> None:
    result = outcome(allocate([request("a", 0.8), request("b", 0.59), request("c", 0.28)], ["u1"], {}))
    assert result == {"a": "u1", "b": None, "c": None}


def test_two_units_serve_top_two_on_different_units() -> None:
    placements = allocate([request("a", 0.9), request("b", 0.7), request("c", 0.1)], ["u1", "u2"], {})
    result = outcome(placements)
    assert {result["a"], result["b"]} == {"u1", "u2"}
    assert result["c"] is None
    assert next(p for p in placements if p.request.id == "c").reason == "CAPACITY"


def test_non_overlapping_requests_all_win() -> None:
    result = outcome(allocate([request("a", 0.2, start=0), request("b", 0.1, start=2)], ["u1"], {}))
    assert result == {"a": "u1", "b": "u1"}


def test_infeasible_request_never_wins() -> None:
    placements = allocate([request("a", 0.99, reason="AFTER_DEADLINE"), request("b", 0.1)], ["u1"], {})
    assert outcome(placements) == {"a": None, "b": "u1"}
    assert placements[0].reason == "AFTER_DEADLINE"


def test_ties_break_by_creation_time_then_id() -> None:
    assert outcome(allocate([request("b", 0.5, created=1), request("a", 0.5, created=5)], ["u1"], {}))["a"] == "u1"
    assert outcome(allocate([request("b", 0.5), request("a", 0.5)], ["u1"], {}))["a"] == "u1"


def test_existing_locks_are_respected() -> None:
    locked = {"u1": [Interval(start=T0, end=T0 + timedelta(hours=1))]}
    assert outcome(allocate([request("a", 0.9), request("b", 0.8)], ["u1", "u2"], locked)) == {"a": "u2", "b": None}


def test_same_user_is_not_double_booked() -> None:
    placements = allocate([request("a", 0.9, user="u-x"), request("b", 0.8, user="u-x")], ["u1", "u2"], {})
    assert outcome(placements)["b"] is None
    assert placements[1].reason == "USER_OVERLAP"


def test_deterministic_and_empty() -> None:
    requests = [request("a", 0.4), request("b", 0.4), request("c", 0.7)]
    assert outcome(allocate(requests, ["u1"], {})) == outcome(allocate(list(reversed(requests)), ["u1"], {}))
    assert allocate([], ["u1"], {}) == []
