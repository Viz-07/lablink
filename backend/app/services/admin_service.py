from datetime import datetime
from typing import Any

from ..core.errors import find, require
from ..domain.constants import ACTIVE
from ..domain.enums import BookingStatus, Role
from ..domain.models import Equipment, User
from ..repositories.base import State
from .alternatives import find_alternatives
from .booking_state import cancel
from .conflict_service import detect_conflicts
from .events import audit, new_id, notify


def save_equipment(
    state: State, actor: User, changes: dict[str, Any], now: datetime, horizon: int, key: str | None = None
) -> Equipment:
    """Validate and persist an audited equipment creation or update."""
    require(actor.role == Role.ADMIN, "FORBIDDEN", "Lab administrator access required.", 403)
    original = find(state.equipment, key, "Equipment") if key else None
    item_id = original.id if original else new_id("eq")
    fields = original.model_dump() if original else {"id": item_id, "created_at": now}
    explicit_nulls = {k for k, value in changes.items() if value is None and k != "required_training"}
    require(not explicit_nulls, "INVALID_FIELDS", "Only the training requirement can be cleared.")
    values = {**fields, **changes, "updated_at": now}
    lab = find(state.labs, values["lab_id"], "Lab")
    values["department_id"] = lab.department_id
    if count := values.pop("units", None):
        values["unit_ids"] = [f"{item_id}-unit-{i + 1}" for i in range(count)]
    item = Equipment.model_validate(values)
    item.capability_tags = list(dict.fromkeys(tag.lower() for tag in item.capability_tags))
    upcoming = [b for b in state.bookings.values() if b.equipment_id == item.id and b.status in ACTIVE and b.end > now]
    if original and item.status == "active":
        require(
            not any(b.unit_id and b.unit_id not in item.unit_ids for b in upcoming),
            "ACTIVE_BOOKINGS",
            "Cancel or reschedule bookings assigned to units being removed.",
            409,
        )
        require(
            not upcoming or original.lab_id == item.lab_id,
            "ACTIVE_BOOKINGS",
            "Move equipment after its active bookings finish.",
            409,
        )
    state.equipment[item.id] = item
    if item.status != "active":
        for booking in upcoming:
            cancel(state, booking, now)
            booking.status = BookingStatus.REALLOCATED
        for booking in upcoming:
            booking.alternatives = find_alternatives(state, booking, state.users[booking.user_id], now, horizon)
            booking.message = f"{item.name} is now {item.status}. Check your booking options."
            notify(
                state,
                now,
                booking.user_id,
                "equipment_unavailable",
                "Equipment availability changed",
                booking.message,
                "/bookings",
            )
    detect_conflicts(state, item, now)
    audit(
        state, now, actor.id, "equipment.update" if original else "equipment.create", item.id, {"status": item.status}
    )
    return item
