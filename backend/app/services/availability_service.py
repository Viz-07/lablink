from datetime import date, datetime, timedelta

from ..domain.constants import ACTIVE, OCCUPIED, SLOT_MINUTES
from ..domain.models import Booking, Equipment, Interval, User
from ..domain.timeslots import (
    IST,
    STEP,
    at_local,
    campus_date,
    ceil_slot,
    minutes,
    opening,
    overlaps,
    slots,
    within_hours,
)
from ..repositories.base import SlotLock, State


def lock_id(unit_id: str, start: datetime) -> str:
    """Build the stable key for one unit and slot start."""
    return f"{unit_id}__{start:%Y%m%dT%H%M}"


def free_units(state: State, item: Equipment, interval: Interval) -> list[str]:
    """Find the equipment units free for an entire interval."""
    if item.status != "active":
        return []
    return [
        unit
        for unit in item.unit_ids
        if all(lock_id(unit, start) not in state.slot_locks for start in slots(interval.start, interval.end))
    ]


def reserve(state: State, booking: Booking, unit_id: str) -> None:
    """Create a lock for each slot covered by a confirmed booking."""
    for start in slots(booking.start, booking.end):
        key = lock_id(unit_id, start)
        state.slot_locks[key] = SlotLock(id=key, booking_id=booking.id, unit_id=unit_id, slot_start=start)


def release(state: State, booking: Booking) -> None:
    """Remove all slot locks belonging to a booking."""
    if booking.unit_id:
        for start in slots(booking.start, booking.end):
            state.slot_locks.pop(lock_id(booking.unit_id, start), None)


def usage_in_week(state: State, user: User, item: Equipment, start: datetime, exclude: str | None = None) -> int:
    """Count the user's booked minutes on the equipment during the campus week."""
    day = campus_date(start)
    monday = day - timedelta(days=day.weekday())
    window = Interval(start=at_local(monday), end=at_local(monday + timedelta(days=7)))
    return sum(
        minutes(Interval(start=max(b.start, window.start), end=min(b.end, window.end)))
        for b in state.bookings.values()
        if b.id != exclude
        and b.user_id == user.id
        and b.equipment_id == item.id
        and b.status in ACTIVE | OCCUPIED
        and overlaps(b, window)
    )


def user_busy(
    state: State, user: User, interval: Interval, exclude: str | None = None, *, confirmed_only: bool = False
) -> bool:
    """Check whether the user has a conflicting booking."""
    statuses = OCCUPIED if confirmed_only else ACTIVE
    return any(
        b.user_id == user.id and b.id != exclude and b.status in statuses and overlaps(b, interval)
        for b in state.bookings.values()
    )


def eligibility(user: User, item: Equipment) -> list[str]:
    """Explain any equipment status or training barriers to booking."""
    reasons = []
    if item.status != "active":
        reasons.append("This item is currently unavailable.")
    if item.required_training and item.required_training not in user.certifications:
        reasons.append(
            f"Training required: {item.required_training.replace('-', ' ')}. Contact the lab to arrange certification."
        )
    return reasons


def availability(state: State, user: User, item: Equipment, start: date, days: int, now: datetime) -> dict:
    """Build the daily availability slots and their display states."""
    lab = state.labs[item.lab_id]
    result = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        windows = opening(lab, day)
        cells = []
        for time in slots(at_local(day, "08:00"), at_local(day, "20:00")):
            interval = Interval(start=time, end=time + STEP)
            open_slot = within_hours(lab, interval)
            free = free_units(state, item, interval) if open_slot else []
            mine = any(
                state.bookings[lock.booking_id].user_id == user.id
                for unit in item.unit_ids
                if (lock := state.slot_locks.get(lock_id(unit, time))) is not None
            )
            status = (
                "past"
                if time < now
                else "closed"
                if not open_slot
                else "mine"
                if mine
                else "full"
                if not free
                else "free"
                if len(free) == len(item.unit_ids)
                else "partial"
            )
            cells.append(
                {**interval.model_dump(), "free_units": len(free), "total_units": len(item.unit_ids), "state": status}
            )
        result.append({"date": day, "open_windows": windows, "slots": cells})
    return {"slot_minutes": SLOT_MINUTES, "days": result}


def free_windows(
    state: State,
    item: Equipment,
    user: User,
    duration: int,
    earliest: datetime,
    latest: datetime,
    exclude: str | None = None,
):
    """Find candidate time windows with a free unit for the requested duration."""
    if eligibility(user, item) or duration > item.max_booking_minutes:
        return
    day = campus_date(earliest)
    while day <= campus_date(latest):
        for window in opening(state.labs[item.lab_id], day):
            for start in slots(ceil_slot(max(earliest, window.start)), min(latest, window.end)):
                end = start + timedelta(minutes=duration)
                if end > min(latest, window.end):
                    break
                interval = Interval(start=start, end=end)
                units = free_units(state, item, interval)
                if (
                    units
                    and not user_busy(state, user, interval, exclude)
                    and (
                        usage_in_week(state, user, item, start, exclude) + duration
                        <= item.weekly_limit_minutes_per_user
                    )
                ):
                    yield interval, units[0]
        day += timedelta(days=1)


def suggest_slots(
    state: State,
    item: Equipment,
    user: User,
    duration: int,
    earliest: datetime,
    latest: datetime,
    part_of_day: str | None,
) -> list[dict]:
    """Rank up to five available slots by timing, preference, and demand."""
    if earliest > latest:
        return []
    hours = {"morning": range(8, 12), "afternoon": range(12, 17), "evening": range(17, 20)}
    preferred = hours.get(part_of_day or "", range(24))
    choices = []
    for interval, _ in free_windows(state, item, user, duration, earliest, latest):
        match = interval.start.astimezone(IST).hour in preferred
        queued = sum(
            b.equipment_id == item.id and b.status.value in {"pending_approval", "contested"} and overlaps(b, interval)
            for b in state.bookings.values()
        )
        rank = (interval.start - earliest).total_seconds() / (7 * 86400) - 0.2 * match - 0.1 * (queued == 0)
        reason = "Matches your time preference" if part_of_day and match else "Available within lab hours"
        choices.append((rank, interval, reason))
    return [
        {**interval.model_dump(), "unit_available": True, "reason": reason}
        for _, interval, reason in sorted(choices, key=lambda value: (value[0], value[1].start))[:5]
    ]
