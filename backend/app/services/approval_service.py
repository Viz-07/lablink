from datetime import datetime

from ..core.errors import AppError, require
from ..domain.constants import QUEUE
from ..domain.enums import BookingStatus
from ..domain.models import AccessGrant, AccessRequest, Booking, User
from ..domain.timeslots import campus_date, minutes
from ..repositories.base import State
from .alternatives import find_alternatives
from .availability_service import free_units
from .booking_state import confirm, feasibility
from .conflict_service import detect_conflicts
from .events import audit, new_id, notify
from .permissions import must_review


def review_booking(
    state: State,
    actor: User,
    booking: Booking,
    approve: bool,
    comment: str,
    now: datetime,
    horizon: int,
) -> Booking | AppError:
    """Apply a review decision and confirm eligible bookings when possible."""
    must_review(actor, state, booking)
    require(booking.status in QUEUE, "ALREADY_REVIEWED", "This booking has already been reviewed.", 409)
    require(booking.start > now, "PAST_SLOT", "This booking window has already started.", 409)
    item, user = state.equipment[booking.equipment_id], state.users[booking.user_id]
    if approve:
        conflict = state.conflicts.get(booking.conflict_id or "")
        require(
            not conflict or conflict.status != "open", "IN_CONFLICT", "Review this booking in Conflict Center.", 409
        )
        if issue := feasibility(state, item, user, booking, now):
            raise AppError(*issue)
        units = free_units(state, item, booking)
        if not units:
            booking.status = BookingStatus.CONTESTED
            detect_conflicts(state, item, now)
            return AppError("IN_CONFLICT", "The slot became contested. Review it in Conflict Center.", 409)
        confirm(state, booking, units[0], now, actor.id)
    else:
        require(len(comment) >= 5, "COMMENT_REQUIRED", "Give a reason of at least five characters.")
        booking.status, booking.updated_at, booking.message = BookingStatus.DECLINED, now, comment
        booking.alternatives = find_alternatives(state, booking, user, now, horizon)
        notify(state, now, booking.user_id, "booking_declined", "Booking declined", comment, "/bookings")
    detect_conflicts(state, item, now)
    audit(state, now, actor.id, "approval.approve" if approve else "approval.decline", booking.id)
    return booking


def flags(state: State, entry: Booking | AccessRequest, actor: User, now: datetime) -> list[dict[str, str]]:
    """Identify deterministic risks relevant to an approval decision."""
    user = state.users[entry.user_id if isinstance(entry, Booking) else entry.requester_id]
    items = [
        state.equipment[i] for i in (entry.equipment_ids if isinstance(entry, AccessRequest) else [entry.equipment_id])
    ]
    project = state.projects.get(entry.project_id or "")
    checks = [
        (
            any(e.required_training and e.required_training not in user.certifications for e in items),
            "MISSING_TRAINING",
            "Certification is missing",
        ),
        (
            bool(project and project.deadline and project.deadline < campus_date(now)),
            "DEADLINE_PASSED",
            "Project deadline has passed",
        ),
        (isinstance(entry, AccessRequest) and entry.hours_requested > 20, "HIGH_HOURS", "More than 20 hours requested"),
        (any(e.high_demand for e in items), "HIGH_DEMAND_EQUIPMENT", "High-demand equipment"),
        (
            isinstance(entry, Booking)
            and bool(entry.conflict_id and state.conflicts[entry.conflict_id].status == "open"),
            "OVERLAPS_CONFLICT",
            "Request belongs to an open conflict",
        ),
        (user.no_show_count >= 2, "REPEAT_NO_SHOWS", "Multiple prior no-shows"),
        (
            isinstance(entry, AccessRequest) and len(entry.justification.split()) < 40,
            "VAGUE_JUSTIFICATION",
            "Justification is brief",
        ),
        (
            bool(project and project.supervisor_id and project.supervisor_id != actor.id),
            "NOT_SUPERVISOR_PROJECT",
            "Another faculty member supervises this project",
        ),
    ]
    return [{"code": code, "message": message} for active, code, message in checks if active]


def review_access(
    state: State,
    actor: User,
    entry: AccessRequest,
    approve: bool,
    comment: str,
    hours: int | None,
    now: datetime,
) -> dict:
    """Record an access decision and issue a grant when approved."""
    must_review(actor, state, entry)
    require(entry.status == "pending", "ALREADY_REVIEWED", "This request has already been reviewed.", 409)
    grant = None
    if approve:
        require(entry.needed_until >= campus_date(now), "REQUEST_EXPIRED", "This access window has ended.", 409)
        approved = hours or entry.hours_requested
        require(approved <= entry.hours_requested, "INVALID_QUOTA", "Approve no more than the requested hours.")
        grant = AccessGrant(
            id=new_id("ag"),
            access_request_id=entry.id,
            user_id=entry.requester_id,
            project_id=entry.project_id,
            equipment_ids=entry.equipment_ids,
            minutes_quota=approved * 60,
            valid_from=entry.needed_from,
            valid_until=entry.needed_until,
        )
        state.access_grants[grant.id] = grant
    else:
        require(len(comment) >= 5, "COMMENT_REQUIRED", "Give a reason of at least five characters.")
    entry.status = "approved" if approve else "declined"
    entry.reviewer_id, entry.reviewer_comment, entry.decided_at = actor.id, comment, now
    notify(
        state,
        now,
        entry.requester_id,
        f"access_{entry.status}",
        f"Project access {entry.status}",
        comment or state.projects[entry.project_id].title,
        "/projects",
    )
    audit(state, now, actor.id, f"access.{entry.status}", entry.id)
    return {"request": entry, "grant": grant}


def approval_item(state: State, entry: AccessRequest | Booking, actor: User, now: datetime) -> dict:
    """Build a review queue record with contextual details and flags."""
    is_booking = isinstance(entry, Booking)
    requester_id = entry.user_id if is_booking else entry.requester_id
    user = state.users[requester_id]
    keys = [entry.equipment_id] if is_booking else entry.equipment_ids
    return {
        "type": "booking" if is_booking else "access",
        "id": entry.id,
        "requester": user.name,
        "equipment": [state.equipment[k].name for k in keys],
        "project": state.projects.get(entry.project_id or ""),
        "created_at": entry.created_at,
        "justification": entry.purpose if is_booking else entry.justification,
        "hours": minutes(entry) / 60 if is_booking else entry.hours_requested,
        "start": entry.start if is_booking else entry.needed_from,
        "end": entry.end if is_booking else entry.needed_until,
        "flags": flags(state, entry, actor, now),
        "conflict_id": entry.conflict_id
        if is_booking and entry.conflict_id and state.conflicts[entry.conflict_id].status == "open"
        else None,
    }
