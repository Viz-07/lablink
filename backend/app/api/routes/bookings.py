from typing import Literal

from fastapi import APIRouter

from ...core.errors import find, require
from ...domain.constants import ACTIVE
from ...domain.enums import BookingStatus
from ...domain.models import Booking
from ...repositories.base import State
from ...services.booking_service import accept_alternative, cancel_booking, create_booking
from ...services.catalog_service import page
from ...services.permissions import can_review
from ..deps import SignedIn
from ..schemas import BookingCreate, Cancel, Id, Selection
from .catalog import PageLimit

router = APIRouter(prefix="/bookings", tags=["bookings"])


def serialize(state: State, booking: Booking) -> dict:
    item = state.equipment[booking.equipment_id]
    return {**booking.model_dump(), "equipment_name": item.name, "lab_name": state.labs[item.lab_id].name}


@router.post("", status_code=201)
def create(s: SignedIn, payload: BookingCreate) -> dict:
    def operation(state, user):
        result = create_booking(
            state,
            user,
            payload.equipment_id,
            payload.start,
            payload.end,
            payload.purpose,
            payload.project_id,
            s.now,
            s.horizon,
        )
        return serialize(state, result) if isinstance(result, Booking) else result

    return s.mutate(operation)


@router.get("/mine")
def mine(
    s: SignedIn,
    status: BookingStatus | None = None,
    when: Literal["upcoming", "past", "action"] = "upcoming",
    limit: PageLimit = 20,
    cursor: str | None = None,
) -> dict:
    def matches(booking: Booking) -> bool:
        if when == "action":
            return (booking.end > s.now and booking.status in {BookingStatus.CONTESTED, BookingStatus.REALLOCATED}) or (
                booking.end > s.now and booking.status == BookingStatus.PENDING and booking.conflict_id is not None
            )
        if when == "past":
            return booking.end <= s.now or booking.status in {
                BookingStatus.CANCELLED,
                BookingStatus.DECLINED,
                BookingStatus.COMPLETED,
                BookingStatus.NO_SHOW,
            }
        return booking.end > s.now and booking.status in ACTIVE and not booking.conflict_id

    entries = sorted(
        (
            b
            for b in s.state.bookings.values()
            if b.user_id == s.user.id and (not status or b.status == status) and matches(b)
        ),
        key=lambda b: b.start,
        reverse=when == "past",
    )
    return page([serialize(s.state, booking) for booking in entries], limit, cursor)


@router.get("/{key}")
def booking(s: SignedIn, key: Id) -> dict:
    entry = find(s.state.bookings, key, "Booking")
    require(
        s.user.id == entry.user_id or can_review(s.user, s.state, entry),
        "FORBIDDEN",
        "This booking is outside your account.",
        403,
    )
    return serialize(s.state, entry)


@router.post("/{key}/cancel")
def cancel(s: SignedIn, key: Id, payload: Cancel | None = None) -> dict:
    return s.mutate(
        lambda state, user: serialize(state, cancel_booking(state, user, find(state.bookings, key, "Booking"), s.now))
    )


@router.post("/{key}/accept-alternative", status_code=201)
def accept(s: SignedIn, key: Id, payload: Selection) -> dict:
    def operation(state, user):
        result = accept_alternative(state, user, find(state.bookings, key, "Booking"), payload.index, s.now, s.horizon)
        return serialize(state, result) if isinstance(result, Booking) else result

    return s.mutate(operation)
