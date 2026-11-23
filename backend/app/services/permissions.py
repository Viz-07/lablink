from ..core.errors import require
from ..domain.enums import Role
from ..domain.models import AccessRequest, Booking, Equipment, User
from ..repositories.base import State


def supervises(user: User, state: State, item: Equipment) -> bool:
    return user.role == Role.ADMIN or (user.role == Role.FACULTY and user.id in state.labs[item.lab_id].supervisor_ids)


def can_review(user: User, state: State, record: Booking | AccessRequest) -> bool:
    project = state.projects.get(record.project_id or "")
    if user.role == Role.ADMIN:
        return True
    if (
        user.role != Role.FACULTY or record.requester_id == user.id
        if isinstance(record, AccessRequest)
        else user.role != Role.FACULTY or record.user_id == user.id
    ):
        return False
    if project and project.supervisor_id == user.id:
        return True
    keys = [record.equipment_id] if isinstance(record, Booking) else record.equipment_ids
    return all(supervises(user, state, state.equipment[key]) for key in keys)


def must_review(user: User, state: State, record: Booking | AccessRequest) -> None:
    require(can_review(user, state, record), "FORBIDDEN", "This request is outside your review scope.", 403)
