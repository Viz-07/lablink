from datetime import date, datetime
from typing import Any

from ..core.errors import find, require
from ..domain.enums import Role
from ..domain.models import AccessRequest, Project, User
from ..domain.timeslots import campus_date
from ..repositories.base import State
from .events import audit, new_id, notify
from .permissions import can_review


def my_projects(state: State, user: User) -> list[Project]:
    """List projects associated with the current user."""
    return [p for p in state.projects.values() if user.id in {p.owner_id, *p.member_ids}]


def project_for(state: State, user: User, project_id: str) -> Project:
    """Look up a project and require the user to be an owner or member."""
    project = find(state.projects, project_id, "Project")
    require(
        user.id in {project.owner_id, *project.member_ids}, "FORBIDDEN", "This project is outside your account.", 403
    )
    return project


def save_project(
    state: State,
    user: User,
    values: dict[str, Any],
    now: datetime,
    project_id: str | None = None,
) -> Project:
    """Validate and save a new or updated project."""
    if project_id:
        previous = find(state.projects, project_id, "Project")
        require(previous.owner_id == user.id, "FORBIDDEN", "Only the owner can edit the project.", 403)
        fields = {**previous.model_dump(), **values}
    else:
        fields = {**values, "id": new_id("pr"), "owner_id": user.id, "created_at": now}
    if fields.get("supervisor_id"):
        supervisor = find(state.users, fields["supervisor_id"], "Supervisor")
        require(supervisor.role == Role.FACULTY, "INVALID_SUPERVISOR", "Choose a faculty supervisor.")
    for key in fields.get("member_ids", []):
        require(key in state.users, "INVALID_MEMBER", "Choose a registered project member.")
    if fields.get("deadline") and (not project_id or "deadline" in values):
        require(fields["deadline"] >= campus_date(now), "PAST_DEADLINE", "The deadline must be today or later.")
    project = Project.model_validate(fields)
    state.projects[project.id] = project
    audit(state, now, user.id, "project.update" if project_id else "project.create", project.id)
    return project


def create_request(
    state: State,
    user: User,
    project_id: str,
    equipment_ids: list[str],
    hours: int,
    earliest: date,
    latest: date,
    justification: str,
    now: datetime,
) -> AccessRequest:
    """Create a pending project equipment access request."""
    project = project_for(state, user, project_id)
    require(campus_date(now) <= earliest <= latest, "INVALID_DATES", "Check the start and end dates.")
    require(
        not project.deadline or latest <= project.deadline, "AFTER_DEADLINE", "Access must end by the project deadline."
    )
    items = [find(state.equipment, key, "Equipment") for key in dict.fromkeys(equipment_ids)]
    require(all(item.status == "active" for item in items), "EQUIPMENT_UNAVAILABLE", "Select active equipment.")
    request = AccessRequest(
        id=new_id("ar"),
        project_id=project.id,
        requester_id=user.id,
        equipment_ids=[item.id for item in items],
        hours_requested=hours,
        needed_from=earliest,
        needed_until=latest,
        justification=justification,
        created_at=now,
    )
    reviewers = [reviewer for reviewer in state.users.values() if can_review(reviewer, state, request)]
    require(reviewers, "NO_REVIEWER", "Choose a project supervisor to review these items.")
    state.access_requests[request.id] = request
    for reviewer in reviewers:
        notify(state, now, reviewer.id, "approval_needed", "New project access request", project.title, "/approvals")
    audit(state, now, user.id, "access.create", request.id)
    return request


def withdraw(state: State, user: User, entry: AccessRequest, now: datetime) -> AccessRequest:
    """Withdraw a pending access request belonging to the user."""
    require(entry.requester_id == user.id, "FORBIDDEN", "Only the requester can withdraw this request.", 403)
    require(entry.status == "pending", "ALREADY_REVIEWED", "This request has already been reviewed.", 409)
    entry.status, entry.decided_at = "withdrawn", now
    audit(state, now, user.id, "access.withdraw", entry.id)
    return entry
