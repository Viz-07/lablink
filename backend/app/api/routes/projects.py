from fastapi import APIRouter

from ...core.errors import find
from ...domain.models import AccessRequest, Project
from ...services.project_service import create_request, my_projects, save_project, withdraw
from ..deps import SignedIn
from ..schemas import AccessCreate, Id, ProjectCreate, ProjectUpdate

router = APIRouter(tags=["projects"])


@router.get("/projects/mine")
def mine(s: SignedIn) -> list[Project]:
    return my_projects(s.state, s.user)


@router.post("/projects", status_code=201)
def create(s: SignedIn, payload: ProjectCreate) -> Project:
    return s.mutate(lambda state, user: save_project(state, user, payload.model_dump(), s.now))


@router.patch("/projects/{key}")
def update(s: SignedIn, key: Id, payload: ProjectUpdate) -> Project:
    changes = payload.model_dump(exclude_unset=True)
    return s.mutate(lambda state, user: save_project(state, user, changes, s.now, key))


@router.get("/access-requests/mine")
def requests(s: SignedIn) -> list[AccessRequest]:
    return [item for item in s.state.access_requests.values() if item.requester_id == s.user.id]


@router.get("/access-grants/mine")
def grants(s: SignedIn) -> list[dict]:
    return [
        {**g.model_dump(), "remaining_minutes": g.minutes_quota - g.minutes_used}
        for g in s.state.access_grants.values()
        if g.user_id == s.user.id
    ]


@router.post("/access-requests", status_code=201)
def create_access(s: SignedIn, payload: AccessCreate) -> AccessRequest:
    return s.mutate(
        lambda state, user: create_request(
            state,
            user,
            payload.project_id,
            payload.equipment_ids,
            payload.hours_requested,
            payload.needed_from,
            payload.needed_until,
            payload.justification,
            s.now,
        )
    )


@router.post("/access-requests/{key}/withdraw")
def withdraw_access(s: SignedIn, key: Id) -> AccessRequest:
    return s.mutate(lambda state, user: withdraw(state, user, find(state.access_requests, key, "Request"), s.now))
