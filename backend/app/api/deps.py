from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, cast

from fastapi import Depends, Request

from ..ai.ai_service import AIService
from ..core.clock import Clock
from ..core.config import Settings
from ..core.errors import AppError, require
from ..core.security import token_user
from ..domain.enums import Role
from ..domain.models import User
from ..repositories.base import Repository, State


@dataclass
class Context:
    settings: Settings
    repo: Repository
    ai: AIService
    now: datetime


def context(request: Request) -> Context:
    clock = cast(Clock, request.app.state.clock)
    return Context(request.app.state.settings, request.app.state.repo, request.app.state.ai, clock.now())


Ctx = Annotated[Context, Depends(context)]


class Session:
    def __init__(self, ctx: Context, user_id: str, state: State) -> None:
        self.ctx, self.state, self.user = ctx, state, self._get_user(state, user_id)
        self.now, self.horizon = ctx.now, ctx.settings.booking_horizon_days

    @staticmethod
    def _get_user(state: State, user_id: str) -> User:
        if user_id not in state.users:
            raise AppError("UNAUTHORIZED", "Sign in to continue.", 401)
        return state.users[user_id]

    def mutate[T](self, operation: Callable[[State, User], T | AppError]) -> T:
        result = self.ctx.repo.transact(lambda state: operation(state, self._get_user(state, self.user.id)))
        if isinstance(result, AppError):
            raise result
        return result


def session(request: Request, ctx: Ctx) -> Session:
    user_id = token_user(ctx.settings, request.cookies.get("ll_session"))
    if not user_id:
        raise AppError("UNAUTHORIZED", "Sign in to continue.", 401)
    return Session(ctx, user_id, ctx.repo.read())


def reviewer(session: Annotated[Session, Depends(session)]) -> Session:
    require(session.user.role in {Role.FACULTY, Role.ADMIN}, "FORBIDDEN", "Faculty access required.", 403)
    return session


def admin(session: Annotated[Session, Depends(session)]) -> Session:
    require(session.user.role == Role.ADMIN, "FORBIDDEN", "Lab administrator access required.", 403)
    return session


SignedIn = Annotated[Session, Depends(session)]
Reviewer = Annotated[Session, Depends(reviewer)]
Admin = Annotated[Session, Depends(admin)]
