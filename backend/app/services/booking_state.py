from datetime import datetime

from ..core.errors import require
from ..domain.enums import BookingStatus
from ..domain.models import Booking, Equipment, User
from ..domain.timeslots import campus_date, minutes, within_hours
from ..repositories.base import State
from .access import valid_grant
from .availability_service import eligibility, free_units, release, reserve, usage_in_week, user_busy
from .events import notify


def feasibility(state: State, item: Equipment, user: User, booking: Booking, now: datetime) -> tuple[str, str] | None:
    project = state.projects.get(booking.project_id or "")
    if booking.start < now:
        return "PAST_SLOT", "Choose a time in the future."
    if item.status != "active":
        return "EQUIPMENT_UNAVAILABLE", "This item is currently unavailable."
    if reasons := eligibility(user, item):
        return "MISSING_TRAINING", reasons[0]
    if project and project.deadline and campus_date(booking.end) > project.deadline:
        return "AFTER_DEADLINE", "The booking ends after the project deadline."
    if not within_hours(state.labs[item.lab_id], booking):
        return "LAB_CLOSED", "Choose a slot within one lab opening window."
    if minutes(booking) > item.max_booking_minutes:
        return "DURATION_LIMIT", f"This item can be booked for up to {item.max_booking_minutes} minutes."
    if user_busy(state, user, booking, booking.id, confirmed_only=True):
        return "USER_OVERLAP", "This overlaps a confirmed booking."
    if (
        usage_in_week(state, user, item, booking.start, booking.id) + minutes(booking)
        > item.weekly_limit_minutes_per_user
    ):
        return "WEEKLY_LIMIT", "This booking exceeds your weekly limit for this equipment."
    return None


def confirm(state: State, booking: Booking, unit: str, now: datetime, actor: str | None = None) -> None:
    item, user = state.equipment[booking.equipment_id], state.users[booking.user_id]
    require(unit in free_units(state, item, booking), "SLOT_UNAVAILABLE", "The slot is no longer available.", 409)
    grant = valid_grant(state, user, item, booking.project_id, booking)
    if grant and item.approval_mode == "faculty":
        grant.minutes_used += minutes(booking)
        booking.grant_id = grant.id
    booking.status, booking.unit_id = BookingStatus.CONFIRMED, unit
    booking.approved_by, booking.updated_at = actor, now
    reserve(state, booking, unit)
    notify(state, now, user.id, "booking_confirmed", "Booking confirmed", item.name, "/bookings")


def cancel(state: State, booking: Booking, now: datetime) -> None:
    release(state, booking)
    if grant := state.access_grants.get(booking.grant_id or ""):
        grant.minutes_used = max(0, grant.minutes_used - minutes(booking))
        booking.grant_id = None
    booking.status, booking.updated_at = BookingStatus.CANCELLED, now
