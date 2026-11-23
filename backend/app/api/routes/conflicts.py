from typing import Literal

from fastapi import APIRouter

from ...core.errors import find, require
from ...domain.enums import BookingStatus
from ...domain.models import Conflict, User
from ...repositories.base import State
from ...services.conflict_service import apply, detect_conflicts, propose, request_input
from ...services.events import audit, notify
from ...services.permissions import supervises
from ..deps import Admin, Reviewer
from ..schemas import Apply, Id, Reason

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


def scoped(state: State, user: User, key: str) -> Conflict:
    conflict = find(state.conflicts, key, "Conflict")
    require(
        supervises(user, state, state.equipment[conflict.equipment_id]),
        "FORBIDDEN",
        "This conflict is outside your lab scope.",
        403,
    )
    return conflict


def serialize(s: Reviewer, state: State, item: Conflict, *, detail: bool = False) -> dict:
    equipment = state.equipment[item.equipment_id]
    result = {
        **item.model_dump(),
        "equipment_name": equipment.name,
        "lab_name": state.labs[equipment.lab_id].name,
        "n_requests": len(item.booking_ids),
    }
    if detail:
        result["requests"] = [
            {
                "booking_id": b.id,
                "student": state.users[b.user_id].name,
                "project": state.projects[b.project_id].title if b.project_id else None,
                "breakdown": request_input(state, equipment, b, s.now).priority,
                "start": b.start,
                "end": b.end,
            }
            for key in item.booking_ids
            if (b := state.bookings.get(key)) is not None
        ]
    return result


@router.get("")
def listing(
    s: Reviewer, status: Literal["open", "resolved", "dismissed"] = "open", refresh: bool = False
) -> list[dict]:
    def collect(state, user):
        if refresh:
            for equipment in state.equipment.values():
                if supervises(user, state, equipment):
                    detect_conflicts(state, equipment, s.now)
        return [
            serialize(s, state, c)
            for c in sorted(state.conflicts.values(), key=lambda c: c.window_start)
            if c.status == status
            and supervises(user, state, state.equipment[c.equipment_id])
            and (status != "open" or c.window_end >= s.now)
        ]

    return s.mutate(collect) if refresh else collect(s.state, s.user)


@router.get("/{key}")
def detail(s: Reviewer, key: Id) -> dict:
    return serialize(s, s.state, scoped(s.state, s.user, key), detail=True)


@router.post("/{key}/recommend")
def recommend(s: Reviewer, key: Id) -> dict:
    conflict = scoped(s.state, s.user, key)
    require(conflict.status == "open", "CONFLICT_CLOSED", "This conflict is already closed.", 409)
    rows = propose(s.state, conflict, s.now, s.horizon)
    explanation, source = s.ctx.ai.explain(s.state.equipment[conflict.equipment_id], rows)

    def persist(state, user):
        current = scoped(state, user, key)
        require(
            current.status == "open" and propose(state, current, s.now, s.horizon) == rows,
            "STALE_ALLOCATION",
            "The requests changed. Generate a fresh recommendation.",
            409,
        )
        current.recommendation, current.ai_explanation, current.explanation_source = rows, explanation.summary, source
        current.messages = {message.booking_id: message.text for message in explanation.messages}
        return serialize(s, state, current, detail=True)

    return s.mutate(persist)


@router.post("/{key}/apply")
def apply_allocation(s: Reviewer, key: Id, payload: Apply | None = None) -> dict:
    overrides = [(entry.promote, entry.demote, entry.reason) for entry in payload.overrides] if payload else []
    return s.mutate(
        lambda state, user: serialize(
            s,
            state,
            apply(state, scoped(state, user, key), user.id, s.now, s.horizon, overrides),
            detail=True,
        )
    )


@router.post("/{key}/dismiss")
def dismiss(s: Admin, key: Id, payload: Reason) -> dict:
    def operation(state, user):
        conflict = scoped(state, user, key)
        require(conflict.status == "open", "CONFLICT_CLOSED", "This conflict is already closed.", 409)
        conflict.status, conflict.resolved_by, conflict.resolved_at = "dismissed", user.id, s.now
        for bid in conflict.booking_ids:
            booking = state.bookings[bid]
            booking.status, booking.message = BookingStatus.DECLINED, payload.reason
            notify(state, s.now, booking.user_id, "conflict_closed", "Conflict dismissed", payload.reason, "/bookings")
        audit(state, s.now, user.id, "conflict.dismiss", key)
        return serialize(s, state, conflict, detail=True)

    return s.mutate(operation)
