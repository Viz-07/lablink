"""Unit tests for pure domain logic: priority scoring and time-slot maths."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.domain.constants import PRIORITY_WEIGHTS
from app.domain.enums import ProjectType
from app.domain.models import Interval
from app.domain.priority import priority_score
from app.domain.timeslots import aligned, at_local, campus_date, ceil_slot, minutes, overlaps, slots


def test_weights_sum_to_one() -> None:
    assert sum(PRIORITY_WEIGHTS.values()) == pytest.approx(1.0)


def test_worked_example_orders_capstone_research_personal() -> None:
    capstone = priority_score(6, 120, ProjectType.CAPSTONE, True, 20)
    research = priority_score(20, 0, ProjectType.RESEARCH, False, 30)
    personal = priority_score(None, 300, ProjectType.PERSONAL, False, 2)
    assert capstone.score == pytest.approx(0.8078, abs=1e-4)
    assert research.score == pytest.approx(0.5883, abs=1e-4)
    assert personal.score == pytest.approx(0.2778, abs=1e-4)
    assert capstone.score > research.score > personal.score


@pytest.mark.parametrize(
    ("days", "usage", "waiting", "no_shows"),
    [(0, 0, 0, 0), (45, 10_000, 1_000, 9), (-3, 0, 0, 0), (None, 600, 72, 3)],
)
def test_every_factor_is_bounded(days: int | None, usage: int, waiting: float, no_shows: int) -> None:
    breakdown = priority_score(days, usage, None, False, waiting, no_shows)
    assert all(0.0 <= factor.value <= 1.0 for factor in breakdown.factors.values())
    assert 0.0 <= breakdown.score <= 1.0


def test_caps_on_usage_and_waiting() -> None:
    assert priority_score(5, 600, None, False, 72).factors["fairness"].value == 0.0
    assert priority_score(5, 9_999, None, False, 500).factors["waiting"].value == 1.0


def test_no_shows_reduce_fairness() -> None:
    clean = priority_score(5, 0, None, False, 0).factors["fairness"].value
    penalised = priority_score(5, 0, None, False, 0, no_shows=2).factors["fairness"].value
    assert penalised == pytest.approx(clean - 0.2)


def test_alignment_and_ceiling() -> None:
    nine = at_local(date(2026, 11, 23), "09:00")
    assert aligned(nine)
    assert aligned(nine + timedelta(minutes=30))
    assert not aligned(nine + timedelta(minutes=10))
    assert ceil_slot(nine + timedelta(minutes=1)) == nine + timedelta(minutes=30)
    assert ceil_slot(nine) == nine


def test_touching_intervals_do_not_overlap() -> None:
    start = datetime(2026, 11, 23, 4, 0, tzinfo=UTC)
    first = Interval(start=start, end=start + timedelta(hours=1))
    touching = Interval(start=first.end, end=first.end + timedelta(hours=1))
    inside = Interval(start=start + timedelta(minutes=30), end=start + timedelta(minutes=90))
    assert not overlaps(first, touching)
    assert overlaps(first, inside)
    assert minutes(first) == 60
    assert len(list(slots(first.start, first.end))) == 2


def test_ist_date_across_utc_midnight() -> None:
    late_utc = datetime(2026, 11, 23, 20, 0, tzinfo=UTC)  # 01:30 IST next day
    assert campus_date(late_utc) == date(2026, 11, 24)
    assert at_local(date(2026, 11, 24), "00:00") == datetime(2026, 11, 23, 18, 30, tzinfo=UTC)
