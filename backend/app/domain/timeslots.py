from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .constants import SLOT_MINUTES
from .models import Interval, Lab

IST = ZoneInfo("Asia/Kolkata")
STEP = timedelta(minutes=SLOT_MINUTES)


def campus_date(value: datetime) -> date:
    return value.astimezone(IST).date()


def at_local(day: date, clock: str = "00:00") -> datetime:
    return datetime.combine(day, time.fromisoformat(clock), IST).astimezone(UTC)


def aligned(value: datetime) -> bool:
    local = value.astimezone(IST)
    return local.minute % SLOT_MINUTES == local.second == local.microsecond == 0


def ceil_slot(value: datetime) -> datetime:
    floor = value.replace(minute=value.minute // SLOT_MINUTES * SLOT_MINUTES, second=0, microsecond=0)
    return floor if floor == value else floor + STEP


def slots(start: datetime, end: datetime) -> Iterator[datetime]:
    while start < end:
        yield start
        start += STEP


def overlaps(one: Interval, two: Interval) -> bool:
    return one.start < two.end and two.start < one.end


def minutes(one: Interval) -> int:
    return int((one.end - one.start).total_seconds() // 60)


def opening(lab: Lab, day: date) -> list[Interval]:
    return [
        Interval(start=at_local(day, window.open), end=at_local(day, window.close))
        for window in lab.opening_hours.get(day.weekday(), [])
    ]


def within_hours(lab: Lab, interval: Interval) -> bool:
    return any(
        window.start <= interval.start < interval.end <= window.end
        for window in opening(lab, campus_date(interval.start))
    )
