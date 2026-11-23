from collections import Counter
from datetime import datetime, timedelta

from ..domain.constants import OCCUPIED
from ..domain.models import Alternative, Booking, Equipment, User
from ..domain.timeslots import at_local, campus_date, minutes, opening
from ..repositories.base import State
from .access import valid_grant
from .availability_service import free_windows


def similarity(a: Equipment, b: Equipment) -> float:
    left, right = set(a.capability_tags), set(b.capability_tags)
    return len(left & right) / max(1, len(left | right))


def utilisation(state: State, item: Equipment, now: datetime) -> float:
    start = now - timedelta(days=14)
    capacity = sum(
        minutes(window)
        for n in range(14)
        for window in opening(state.labs[item.lab_id], campus_date(start) + timedelta(days=n))
    ) * len(item.unit_ids)
    used = sum(
        minutes(b)
        for b in state.bookings.values()
        if b.equipment_id == item.id and b.status in OCCUPIED and start <= b.start < now
    )
    return min(1.0, used / max(capacity, 1))


def find_alternatives(
    state: State,
    booking: Booking,
    user: User,
    now: datetime,
    horizon: int = 14,
) -> list[Alternative]:
    original = state.equipment[booking.equipment_id]
    project = state.projects.get(booking.project_id or "")
    deadline = (
        at_local(project.deadline + timedelta(days=1))
        if project and project.deadline
        else booking.start + timedelta(days=5)
    )
    end = min(deadline, now + timedelta(days=horizon))
    start = max(now, booking.start - timedelta(days=3))
    if start > end:
        return []
    candidates = []
    for item in state.equipment.values():
        same = item.id == original.id
        match = similarity(original, item)
        if not same and (item.category != original.category or match < 0.5):
            continue
        bonus = 1 - utilisation(state, item, now)
        for interval, unit in free_windows(state, item, user, minutes(booking), start, end, booking.id):
            if same and interval.start == booking.start:
                continue
            if (
                not same
                and item.approval_mode == "faculty"
                and not valid_grant(state, user, item, booking.project_id, interval)
            ):
                continue
            distance = abs((interval.start - booking.start).total_seconds()) / 3600
            margin = 1 if deadline - interval.end >= timedelta(days=1) else 0.5
            score = 0.5 * (1 - min(distance, 72) / 72) + 0.3 * margin + 0.2 * bonus
            reason = "Same equipment at a nearby time" if same else f"Equivalent capabilities ({match:.0%} tag match)"
            candidates.append(
                Alternative(
                    start=interval.start,
                    end=interval.end,
                    unit_id=unit,
                    equipment_id=item.id,
                    equipment_name=item.name,
                    lab_name=state.labs[item.lab_id].name,
                    score=round(score, 4),
                    type="same_equipment_other_time" if same else "equivalent_equipment",
                    reason=reason,
                )
            )
    counts: Counter[str] = Counter()
    results = []
    for option in sorted(candidates, key=lambda a: (-a.score, a.start, a.equipment_id)):
        if counts[option.equipment_id] < 2:
            results.append(option)
            counts[option.equipment_id] += 1
        if len(results) == 3:
            break
    return results
