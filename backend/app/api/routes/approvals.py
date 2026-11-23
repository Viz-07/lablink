from typing import Literal

from fastapi import APIRouter

from ...core.errors import find
from ...domain.constants import QUEUE
from ...domain.models import AccessRequest, Booking
from ...repositories.base import State
from ...services.approval_service import approval_item, review_access, review_booking
from ...services.permissions import can_review, must_review
from ..deps import Reviewer
from ..schemas import Decision, Id

router = APIRouter(prefix="/approvals", tags=["approvals"])
Kind = Literal["booking", "access"]


def get_entry(state: State, kind: Kind, key: str) -> Booking | AccessRequest:
    return (
        find(state.bookings, key, "Booking")
        if kind == "booking"
        else find(state.access_requests, key, "Access request")
    )


@router.get("")
def items(
    s: Reviewer, type: Literal["booking", "access", "all"] = "all", status: Literal["pending"] = "pending"
) -> list[dict]:
    pending: list[Booking | AccessRequest] = []
    if type != "access":
        pending.extend(b for b in s.state.bookings.values() if b.status in QUEUE and b.start >= s.now)
    if type != "booking":
        pending.extend(r for r in s.state.access_requests.values() if r.status == status)
    return [
        approval_item(s.state, entry, s.user, s.now)
        for entry in sorted(pending, key=lambda item: item.created_at)
        if can_review(s.user, s.state, entry)
    ]


@router.get("/{kind}/{key}/summary")
def summary(s: Reviewer, kind: Kind, key: Id) -> dict:
    entry = get_entry(s.state, kind, key)
    must_review(s.user, s.state, entry)
    item = approval_item(s.state, entry, s.user, s.now)
    result, source = s.ctx.ai.summarize(item)
    return {**result.model_dump(), "source": source, "flags": item["flags"]}


@router.post("/{kind}/{key}/{action}")
def decision(s: Reviewer, kind: Kind, key: Id, action: Literal["approve", "decline"], payload: Decision) -> dict:
    def operation(state, user):
        entry = get_entry(state, kind, key)
        if isinstance(entry, Booking):
            result = review_booking(state, user, entry, action == "approve", payload.comment, s.now, s.horizon)
            return result.model_dump() if isinstance(result, Booking) else result
        return review_access(state, user, entry, action == "approve", payload.comment, payload.hours_approved, s.now)

    return s.mutate(operation)
