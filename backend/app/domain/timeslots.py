from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .constants import SLOT_MINUTES
from .models import Interval, Lab

IST = ZoneInfo("Asia/Kolkata")
STEP = timedelta(minutes=SLOT_MINUTES)


def campus_date(value: datetime) -> date:
    """Return the local campus date of a timestamp."""
    return value.astimezone(IST).date()


def at_local(day: date, clock: str = "00:00") -> datetime:
    """Combine a campus date and local time into a timestamp."""
    return datetime.combine(day, time.fromisoformat(clock), IST).astimezone(UTC)


def aligned(value: datetime) -> bool:
    """Check whether a timestamp falls on a slot boundary."""
    local = value.astimezone(IST)
    return local.minute % SLOT_MINUTES == local.second == local.microsecond == 0


def ceil_slot(value: datetime) -> datetime:
    """Round a timestamp up to the next available slot boundary."""
    floor = value.replace(minute=value.minute // SLOT_MINUTES * SLOT_MINUTES, second=0, microsecond=0)
    return floor if floor == value else floor + STEP


def slots(start: datetime, end: datetime) -> Iterator[datetime]:
    """Yield consecutive slot starts within an interval."""
    while start < end:
        yield start
        start += STEP


def overlaps(one: Interval, two: Interval) -> bool:
    """Check whether two half-open intervals overlap."""
    return one.start < two.end and two.start < one.end


def minutes(one: Interval) -> int:
    """Return the duration of an interval in whole minutes."""
    return int((one.end - one.start).total_seconds() // 60)


def opening(lab: Lab, day: date) -> list[Interval]:
    """Return the lab's opening intervals for a local date."""
    return [
        Interval(start=at_local(day, window.open), end=at_local(day, window.close))
        for window in lab.opening_hours.get(day.weekday(), [])
    ]


def within_hours(lab: Lab, interval: Interval) -> bool:
    """Check whether a booking fits within a single opening interval."""
    return any(
        window.start <= interval.start < interval.end <= window.end
        for window in opening(lab, campus_date(interval.start))
    )
