from datetime import date, datetime, timedelta

from ..ai.ai_service import rank
from ..core.errors import AppError
from ..domain.enums import Category
from ..domain.models import Equipment, User
from ..domain.timeslots import at_local
from ..repositories.base import State
from .alternatives import utilisation
from .availability_service import eligibility, free_windows


def page[T](items: list[T], limit: int, cursor: str | None = None) -> dict:
    """Return a cursor-based page from an ordered list."""
    if cursor and (not cursor.startswith("ll-") or not cursor[3:].isdigit() or len(cursor) > 12):
        raise AppError("BAD_CURSOR", "The page cursor is invalid.")
    offset = int(cursor[3:]) if cursor else 0
    return {
        "items": items[offset : offset + limit],
        "next_cursor": f"ll-{offset + limit}" if offset + limit < len(items) else None,
    }


def summary(state: State, user: User, item: Equipment, now: datetime) -> dict:
    """Build the catalogue summary for a user and equipment item."""
    lab = state.labs[item.lab_id]
    match = next(free_windows(state, item, user, 30, now, now + timedelta(days=7)), None)
    return {
        **item.model_dump(),
        "lab_name": lab.name,
        "lab_room": lab.room,
        "units": len(item.unit_ids),
        "next_free_slot": match[0].start if match else None,
        "utilisation_7d": round(utilisation(state, item, now) * 100, 1),
    }


def list_equipment(
    state: State,
    user: User,
    now: datetime,
    *,
    q: str | None,
    category: Category | None,
    department: str | None,
    lab: str | None,
    kind: str | None,
    available_on: date | None,
    no_training: bool,
    limit: int,
    cursor: str | None,
) -> dict:
    """Filter, sort, and paginate the equipment catalogue."""
    items = [
        item
        for item in state.equipment.values()
        if item.status != "retired"
        and (not category or item.category == category)
        and (not department or item.department_id == department)
        and (not lab or item.lab_id == lab)
        and (not kind or item.kind == kind)
        and (not no_training or not eligibility(user, item))
    ]
    if q:
        hits = {hit.equipment_id for hit in rank(q, items)}
        items = [item for item in items if q.casefold() in item.name.casefold() or item.id in hits]
    if available_on:
        start = max(now, at_local(available_on))
        end = at_local(available_on + timedelta(days=1))
        items = [item for item in items if next(free_windows(state, item, user, 30, start, end), None)]
    listing = page(items, limit, cursor)
    return {**listing, "total": len(items), "items": [summary(state, user, item, now) for item in listing["items"]]}
