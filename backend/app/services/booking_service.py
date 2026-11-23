from datetime import UTC, datetime, timedelta

from ..core.errors import AppError, find, require
from ..domain.constants import ACTIVE, QUEUE
from ..domain.enums import BookingStatus, Role
from ..domain.models import Booking, DemandEvent, User
from ..domain.timeslots import overlaps
from ..repositories.base import State
from .access import valid_grant
from .alternatives import find_alternatives
from .availability_service import free_units, user_busy
from .booking_state import cancel, confirm, feasibility
from .conflict_service import detect_conflicts, promote_after_cancel
from .events import audit, new_id, notify


def create_booking(
    state: State,
    user: User,
    equipment_id: str,
    start: datetime,
    end: datetime,
    purpose: str,
    project_id: str | None,
    now: datetime,
    horizon: int,
    *,
    replacement: bool = False,
) -> Booking | AppError:
    """Validate a booking request and confirm or queue it as appropriate."""
    item = find(state.equipment, equipment_id, "Equipment")
    if project_id:
        project = find(state.projects, project_id, "Project")
        require(user.id in {project.owner_id, *project.member_ids}, "FORBIDDEN", "Select a project you belong to.", 403)
    booking = Booking(
        id=new_id("bk"),
        equipment_id=item.id,
        user_id=user.id,
        project_id=project_id,
        start=start.astimezone(UTC),
        end=end.astimezone(UTC),
        purpose=purpose,
        status=BookingStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    require(
        booking.end <= now + timedelta(days=horizon),
        "OUTSIDE_HORIZON",
        f"Choose a time within the next {horizon} days.",
    )
    if issue := feasibility(state, item, user, booking, now):
        raise AppError(*issue)
    require(not user_busy(state, user, booking), "USER_OVERLAP", "This overlaps one of your existing requests.")
    grant = valid_grant(state, user, item, project_id, booking)
    needs_approval = item.approval_mode == "faculty" and not grant
    require(not needs_approval or project_id, "PROJECT_REQUIRED", "Select a project for faculty approval.")
    units = free_units(state, item, booking)
    competing = sum(
        b.equipment_id == item.id and b.status in QUEUE and overlaps(b, booking) for b in state.bookings.values()
    )
    if not needs_approval and not units:
        event = DemandEvent(id=new_id("de"), equipment_id=item.id, start=booking.start, end=booking.end)
        state.demand_events[event.id] = event
        return AppError(
            "SLOT_UNAVAILABLE",
            "That slot was just taken.",
            409,
            alternatives=find_alternatives(state, booking, user, now, horizon),
        )
    if replacement and (needs_approval or competing + 1 > len(units)):
        return AppError("SLOT_UNAVAILABLE", "This alternative now needs review. Choose another time.", 409)
    state.bookings[booking.id] = booking
    if needs_approval:
        reviewers = set(state.labs[item.lab_id].supervisor_ids)
        project_supervisor = state.projects[project_id or ""].supervisor_id
        if project_supervisor is not None:
            reviewers.add(project_supervisor)
        for reviewer in reviewers:
            notify(state, now, reviewer, "approval_needed", "Booking needs review", item.name, "/approvals")
        notify(state, now, user.id, "booking_pending", "Booking sent for approval", item.name, "/bookings")
    elif competing + 1 > len(units):
        booking.status = BookingStatus.CONTESTED
        notify(state, now, user.id, "contested", "Booking in the allocation queue", item.name, "/bookings")
    else:
        confirm(state, booking, units[0], now)
    detect_conflicts(state, item, now)
    audit(state, now, user.id, "booking.create", booking.id)
    return booking


def cancel_booking(state: State, user: User, booking: Booking, now: datetime) -> Booking:
    """Cancel an eligible booking and reconsider its conflict queue."""
    require(user.id == booking.user_id or user.role == Role.ADMIN, "FORBIDDEN", "You cannot cancel this booking.", 403)
    require(
        booking.status in ACTIVE | {BookingStatus.REALLOCATED}, "CANNOT_CANCEL", "This booking is already closed.", 409
    )
    require(booking.start > now, "CANNOT_CANCEL", "This booking has already started.", 409)
    cancel(state, booking, now)
    notify(
        state,
        now,
        booking.user_id,
        "booking_cancelled",
        "Booking cancelled",
        state.equipment[booking.equipment_id].name,
        "/bookings",
    )
    audit(state, now, user.id, "booking.cancel", booking.id)
    promote_after_cancel(state, booking, now)
    return booking


def accept_alternative(
    state: State, user: User, booking: Booking, index: int, now: datetime, horizon: int
) -> Booking | AppError:
    """Confirm a proposed substitute after rechecking its availability."""
    require(booking.user_id == user.id, "FORBIDDEN", "Only the requester can accept this option.", 403)
    require(
        booking.status == BookingStatus.REALLOCATED,
        "INVALID_STATUS",
        "This booking has no available alternatives.",
        409,
    )
    require(index < len(booking.alternatives), "BAD_ALTERNATIVE", "Select an offered option.")
    choice = booking.alternatives[index]
    result = create_booking(
        state,
        user,
        choice.equipment_id,
        choice.start,
        choice.end,
        booking.purpose,
        booking.project_id,
        now,
        horizon,
        replacement=True,
    )
    if isinstance(result, Booking):
        cancel(state, booking, now)
        booking.replaced_by = result.id
    return result
