from fastapi import APIRouter, Response

from ...core.errors import find, require
from ...core.security import new_token
from ...domain.enums import Role
from ...repositories.base import State
from ...seed.demo_data import PERSONAS
from ...services.events import audit
from ..deps import Ctx, SignedIn
from ..schemas import DemoLogin

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/personas")
def personas(ctx: Ctx) -> list[dict[str, str]]:
    """List the personas available for demo sign-in."""
    require(ctx.settings.demo_mode, "NOT_FOUND", "Demo sign-in is disabled.", 404)
    return [
        {"id": key, "name": name, "role": role.value, "department": department.upper(), "blurb": blurb}
        for key, (name, role, department, _, _, blurb) in PERSONAS.items()
    ]


@router.post("/demo")
def login(payload: DemoLogin, response: Response, ctx: Ctx) -> dict:
    """Sign in as a demo persona and issue a session cookie."""
    require(ctx.settings.demo_mode and payload.persona_id in PERSONAS, "NOT_FOUND", "Demo persona not found.", 404)

    def sign_in(state: State):
        user = find(state.users, payload.persona_id, "Demo persona")
        audit(state, ctx.now, user.id, "auth.sign_in", user.id)
        return user

    user = ctx.repo.transact(sign_in)
    response.set_cookie(
        "ll_session",
        new_token(ctx.settings, user),
        httponly=True,
        samesite="lax",
        secure=ctx.settings.production,
        max_age=ctx.settings.session_ttl_minutes * 60,
    )
    return {"user": user}


@router.post("/logout", status_code=204)
def logout(ctx: Ctx) -> Response:
    """Clear the session cookie."""
    response = Response(status_code=204)
    response.delete_cookie("ll_session", httponly=True, samesite="lax", secure=ctx.settings.production)
    return response


@router.get("/me")
def me(s: SignedIn) -> dict:
    """Return the current user and their available permissions."""
    permissions = ["discover", "bookings", "projects", "notifications"]
    if s.user.role in {Role.FACULTY, Role.ADMIN}:
        permissions.extend(["approvals", "conflicts", "analytics"])
    if s.user.role == Role.ADMIN:
        permissions.append("manage")
    return {"user": s.user, "permissions": permissions, "demo_mode": s.ctx.settings.demo_mode}
