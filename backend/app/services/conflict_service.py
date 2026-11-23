from collections import Counter
from datetime import datetime, timedelta

from ..core.errors import find, require
from ..domain.constants import OCCUPIED, QUEUE
from ..domain.enums import BookingStatus
from ..domain.models import AllocationRow, Booking, Conflict, Equipment, Interval
from ..domain.priority import priority_score
from ..domain.timeslots import STEP, campus_date, minutes, overlaps, slots
from ..repositories.base import State
from .access import valid_grant
from .allocator import RequestInput, allocate
from .alternatives import find_alternatives
from .availability_service import free_units
from .booking_state import confirm, feasibility
from .events import audit, new_id, notify


def groups(bookings: list[Booking]) -> list[list[Booking]]:
    """Group a sorted stream of connected overlapping intervals."""
    out: list[list[Booking]] = []
    end: datetime | None = None
    for booking in sorted(bookings, key=lambda b: (b.start, b.id)):
        if end is None or booking.start >= end:
            out.append([])
            end = booking.end
        end = max(end, booking.end)
        out[-1].append(booking)
    return out


def detect_conflicts(state: State, item: Equipment, now: datetime) -> None:
    """Identify oversubscribed time windows and update conflict records."""
    queued = [b for b in state.bookings.values() if b.equipment_id == item.id and b.status in QUEUE and b.start >= now]
    previous = {c.id: c for c in state.conflicts.values() if c.status == "open" and c.equipment_id == item.id}
    seen = set()
    for booking in queued:
        booking.conflict_id = None
    for group in groups(queued):
        demand = Counter(start for booking in group for start in slots(booking.start, booking.end))
        if all(count <= len(free_units(state, item, Interval(start=t, end=t + STEP))) for t, count in demand.items()):
            continue
        ids = sorted(b.id for b in group)
        existing = next(
            (c for c in previous.values() if c.id not in seen and set(c.booking_ids).intersection(ids)), None
        )
        start, end = min(b.start for b in group), max(b.end for b in group)
        conflict = existing or Conflict(
            id=new_id("cf"), equipment_id=item.id, window_start=start, window_end=end, booking_ids=ids, capacity=0
        )
        if sorted(conflict.booking_ids) != ids:
            conflict.recommendation, conflict.ai_explanation, conflict.explanation_source = None, None, None
            conflict.messages = {}
        conflict.booking_ids, conflict.window_start, conflict.window_end = ids, start, end
        conflict.capacity = len(free_units(state, item, Interval(start=start, end=end)))
        for booking in group:
            booking.conflict_id = conflict.id
        state.conflicts[conflict.id] = conflict
        seen.add(conflict.id)
    for key in previous.keys() - seen:
        previous[key].status = "dismissed"


def request_input(state: State, item: Equipment, booking: Booking, now: datetime) -> RequestInput:
    """Compute the rank and feasibility inputs for a competing booking."""
    user = state.users[booking.user_id]
    project = state.projects.get(booking.project_id or "")
    days = (project.deadline - campus_date(booking.start)).days if project and project.deadline else None
    usage = sum(
        minutes(b)
        for b in state.bookings.values()
        if b.user_id == user.id
        and b.id != booking.id
        and b.status in OCCUPIED
        and now - timedelta(days=7) <= b.start < now
    )
    grant = bool(booking.approved_by or valid_grant(state, user, item, booking.project_id, booking))
    priority = priority_score(
        days,
        usage,
        project.type if project else None,
        grant,
        (now - booking.created_at).total_seconds() / 3600,
        user.no_show_count,
    )
    issue = feasibility(state, item, user, booking, now)
    return RequestInput(booking.id, user.id, booking, booking.created_at, priority, issue[0] if issue else None)


def propose(
    state: State, conflict: Conflict, now: datetime, horizon: int, swaps: dict[str, str] | None = None
) -> list[AllocationRow]:
    """Calculate ranked assignments, then calculate alternatives against the winning locks."""
    item = state.equipment[conflict.equipment_id]
    requests = [request_input(state, item, state.bookings[key], now) for key in conflict.booking_ids]
    locked = {
        unit: [
            Interval(start=lock.slot_start, end=lock.slot_start + STEP)
            for lock in state.slot_locks.values()
            if lock.unit_id == unit
        ]
        for unit in item.unit_ids
    }
    ranked = allocate(requests, item.unit_ids, locked)
    units = {row.request.id: row.unit_id for row in ranked}
    if swaps:
        for promote, demote in swaps.items():
            winner = next((r for r in ranked if r.request.id == demote), None)
            loser = next((r for r in ranked if r.request.id == promote), None)
            require(
                winner and winner.unit_id and loser and loser.reason == "CAPACITY",
                "BAD_OVERRIDE",
                "Choose a recommended winner and a feasible alternative recipient.",
            )
            units[promote], units[demote] = units[demote], None
    working = state.model_copy(deep=True)
    rows = []
    for placement in ranked:
        booking = working.bookings[placement.request.id]
        unit = units[booking.id]
        project = state.projects.get(booking.project_id or "")
        if unit:
            user = working.users[booking.user_id]
            require(
                not feasibility(working, item, user, booking, now),
                "STALE_ALLOCATION",
                "Availability has changed. Refresh the allocation.",
                409,
            )
            confirm(working, booking, unit, now)
        rows.append(
            AllocationRow(
                booking_id=booking.id,
                student=working.users[booking.user_id].name,
                project=project.title if project else None,
                unit_id=unit,
                reason=None if unit else placement.reason or "OVERRIDE",
                breakdown=placement.request.priority,
            )
        )
    for row in rows:
        if not row.unit_id:
            booking = working.bookings[row.booking_id]
            row.alternatives = find_alternatives(working, booking, working.users[booking.user_id], now, horizon)
    return rows


def apply(
    state: State,
    conflict: Conflict,
    actor: str,
    now: datetime,
    horizon: int,
    overrides: list[tuple[str, str, str]],
) -> Conflict:
    """Revalidate and apply a conflict allocation in the current state."""
    require(conflict.status == "open", "CONFLICT_CLOSED", "This conflict is already closed.", 409)
    require(conflict.recommendation, "RECOMMEND_FIRST", "Generate a recommendation before applying it.", 409)
    base = propose(state, conflict, now, horizon)
    prior = {(row.booking_id, row.unit_id) for row in conflict.recommendation or []}
    require(
        prior == {(row.booking_id, row.unit_id) for row in base},
        "STALE_ALLOCATION",
        "Availability has changed. Refresh the recommendation.",
        409,
    )
    swaps = {promote: demote for promote, demote, _ in overrides}
    participants = {key for promote, demote, _ in overrides for key in (promote, demote)}
    require(len(participants) == len(overrides) * 2, "BAD_OVERRIDE", "A request can appear in only one swap.")
    rows = propose(state, conflict, now, horizon, swaps) if swaps else base
    if overrides:
        conflict.ai_explanation, conflict.explanation_source = (
            "A reviewer adjusted the allocation. The updated outcomes are shown below.",
            "fallback",
        )
        conflict.messages = {}
        for promote, demote, reason in overrides:
            audit(
                state,
                now,
                actor,
                "conflict.override",
                conflict.id,
                {"promoted": promote, "demoted": demote, "reason": reason},
            )
    for row in rows:
        booking = state.bookings[row.booking_id]
        booking.priority_snapshot, booking.message = row.breakdown, conflict.messages.get(booking.id)
        if row.unit_id:
            confirm(state, booking, row.unit_id, now, actor)
        else:
            booking.status, booking.updated_at = BookingStatus.REALLOCATED, now
            booking.alternatives = row.alternatives
            notify(
                state,
                now,
                booking.user_id,
                "alternative_offered",
                "New booking options",
                "Your request was reviewed. Open My bookings to see the outcome.",
                "/bookings",
            )
    conflict.status, conflict.recommendation = "resolved", rows
    conflict.resolved_by, conflict.resolved_at = actor, now
    audit(state, now, actor, "conflict.apply", conflict.id, {r.booking_id: r.breakdown.score for r in rows})
    return conflict


def promote_after_cancel(state: State, cancelled: Booking, now: datetime) -> None:
    """Reconsider waiting requests after a booking is cancelled."""
    item = find(state.equipment, cancelled.equipment_id, "Equipment")
    contenders = [
        booking
        for booking in state.bookings.values()
        if booking.equipment_id == item.id
        and booking.status in {BookingStatus.CONTESTED, BookingStatus.REALLOCATED}
        and overlaps(booking, cancelled)
    ]
    ranked = sorted(
        (request_input(state, item, b, now) for b in contenders),
        key=lambda r: (-r.priority.score, r.created_at, r.id),
    )
    for row in ranked:
        booking = state.bookings[row.id]
        if row.reason or feasibility(state, item, state.users[booking.user_id], booking, now):
            continue
        units = free_units(state, item, booking)
        if units:
            confirm(state, booking, units[0], now)
            booking.alternatives = []
            booking.priority_snapshot = row.priority
            notify(state, now, booking.user_id, "slot_opened", "A slot opened up", item.name, "/bookings")
    detect_conflicts(state, item, now)
