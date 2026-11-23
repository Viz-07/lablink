from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from ...core.errors import find, require
from ...domain.enums import Category, Role
from ...domain.models import Department, Lab
from ...domain.timeslots import at_local, campus_date
from ...services.availability_service import availability, eligibility, suggest_slots
from ...services.catalog_service import list_equipment, summary
from ..deps import SignedIn
from ..schemas import Id

router = APIRouter(tags=["catalogue"])
PageLimit = Annotated[int, Query(ge=1, le=100)]


@router.get("/departments")
def departments(s: SignedIn) -> list[Department]:
    """List the departments represented in the catalogue."""
    return list(s.state.departments.values())


@router.get("/labs")
def labs(s: SignedIn, department_id: Id | None = None) -> list[Lab]:
    """List the laboratories available in the catalogue."""
    return [lab for lab in s.state.labs.values() if not department_id or lab.department_id == department_id]


@router.get("/faculty")
def faculty(s: SignedIn) -> list[dict[str, str]]:
    """List faculty members who can supervise a project."""
    return [
        {"id": u.id, "name": u.name, "department": u.department_id.upper()}
        for u in s.state.users.values()
        if u.role == Role.FACULTY
    ]


@router.get("/equipment")
def equipment(
    s: SignedIn,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category: Category | None = None,
    department_id: Id | None = None,
    lab_id: Id | None = None,
    kind: Literal["equipment", "dev_kit", "workstation"] | None = None,
    available_on: date | None = None,
    no_training: bool = False,
    limit: PageLimit = 20,
    cursor: str | None = None,
) -> dict:
    """Return a filtered and paginated equipment catalogue."""
    return list_equipment(
        s.state,
        s.user,
        s.now,
        q=q,
        category=category,
        department=department_id,
        lab=lab_id,
        kind=kind,
        available_on=available_on,
        no_training=no_training,
        limit=limit,
        cursor=cursor,
    )


@router.get("/equipment/{key}")
def detail(s: SignedIn, key: Id) -> dict:
    """Return equipment details and rules for the signed-in user."""
    item = find(s.state.equipment, key, "Equipment")
    reasons = eligibility(s.user, item)
    return {
        **summary(s.state, s.user, item, s.now),
        "lab": s.state.labs[item.lab_id],
        "eligibility": {"can_book": not reasons, "reasons": reasons},
    }


@router.get("/equipment/{key}/availability")
def equipment_availability(
    s: SignedIn,
    key: Id,
    start: Annotated[date | None, Query(alias="from")] = None,
    days: Annotated[int, Query(ge=1, le=14)] = 14,
) -> dict:
    """Return the requested number of days of slot availability."""
    item = find(s.state.equipment, key, "Equipment")
    day = start or campus_date(s.now)
    today = campus_date(s.now)
    require(
        today - timedelta(days=14) <= day <= today + timedelta(days=s.horizon),
        "OUTSIDE_HORIZON",
        "Choose a date near the booking window.",
    )
    return availability(s.state, s.user, item, day, days, s.now)


@router.get("/equipment/{key}/suggest-slots")
def equipment_suggest(
    s: SignedIn,
    key: Id,
    duration_minutes: Annotated[int, Query(ge=30, le=480, multiple_of=30)] = 60,
    earliest: date | None = None,
    latest: date | None = None,
    part_of_day: Literal["morning", "afternoon", "evening"] | None = None,
) -> dict:
    """Suggest feasible slots for a requested duration and time range."""
    item = find(s.state.equipment, key, "Equipment")
    start = max(s.now, at_local(earliest)) if earliest else s.now
    horizon = s.now + timedelta(days=s.horizon)
    end = (
        min(horizon, at_local(latest + timedelta(days=1)))
        if latest and latest < campus_date(horizon)
        else min(horizon, s.now + timedelta(days=7))
        if not latest
        else horizon
    )
    return {"suggestions": suggest_slots(s.state, item, s.user, duration_minutes, start, end, part_of_day)}
