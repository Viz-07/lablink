import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from .ai.ai_service import AIService, build_ai_service
from .api.routes import (
    admin,
    ai,
    analytics,
    approvals,
    auth,
    bookings,
    catalog,
    conflicts,
    health,
    notifications,
    projects,
)
from .core.clock import Clock, SystemClock
from .core.config import Settings, load_settings
from .core.errors import AppError
from .core.middleware import SecurityMiddleware, error_data
from .repositories.base import Repository
from .repositories.factory import build_repository
from .seed.demo_data import seed

LOG = logging.getLogger("lablink")


class Assets(StaticFiles):
    """Serve fingerprinted frontend assets with long-lived caching."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        """Mark the static asset response as cacheable and immutable."""
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


def errors(app: FastAPI) -> None:
    """Register the API handlers that produce structured error responses."""

    @app.exception_handler(AppError)
    async def app_error(request: Request, error: AppError) -> JSONResponse:
        return JSONResponse(
            jsonable_encoder(error_data(error.code, error.message, request.state.request_id, error.details)),
            error.status,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        fields = [
            {"field": ".".join(str(p) for p in issue["loc"]), "message": issue["msg"]} for issue in error.errors()
        ]
        return JSONResponse(
            error_data(
                "VALIDATION_FAILED", "Check the highlighted fields.", request.state.request_id, {"fields": fields}
            ),
            422,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        return JSONResponse(
            error_data("HTTP_ERROR", str(error.detail), request.state.request_id),
            error.status_code,
            headers=error.headers,
        )


class HandleUnexpected:
    """Log unhandled errors and return a generic JSON response."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def track(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, track)
        except Exception:
            request_id = scope["state"]["request_id"]
            LOG.exception("Unhandled request %s", request_id)
            if started:
                raise
            await JSONResponse(error_data("INTERNAL_ERROR", "Something went wrong.", request_id), 500)(
                scope, receive, send
            )


def mount_spa(app: FastAPI, static_dir: Path) -> None:
    """Serve built assets and route non-API navigation to the SPA."""
    if (static_dir / "assets").is_dir():
        app.mount("/assets", Assets(directory=static_dir / "assets"), name="assets")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def spa(path: str) -> Response:
        if path == "api" or path.startswith(("api/", "assets/")):
            raise AppError("NOT_FOUND", "This route does not exist.", 404)
        target = static_dir / "favicon.svg" if path == "favicon.svg" else static_dir / "index.html"
        if not target.is_file():
            raise AppError("FRONTEND_NOT_BUILT", "Build the frontend or open the Vite dev server.", 503)
        return FileResponse(target, headers={"Cache-Control": "no-cache"})


def create_app(
    settings: Settings | None = None,
    repo: Repository | None = None,
    ai_service: AIService | None = None,
    clock: Clock | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    """Configure the application with injectable storage, AI, clock, and static files."""
    config = settings or load_settings()
    repository, timer = repo or build_repository(config), clock or SystemClock()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        LOG.info(
            "Starting LabLink storage=%s ai_enabled=%s model=%s demo_mode=%s production=%s",
            config.storage,
            bool(app.state.ai.client),
            config.gemini_model,
            config.demo_mode,
            config.production,
        )
        if config.production and config.storage == "memory":
            LOG.warning("Memory storage: run with exactly one instance (--max-instances 1)")
        if config.seed_demo_data:
            repository.transact(lambda state: seed(state, timer.now()))
        yield

    app = FastAPI(
        title="LabLink API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if config.production else "/api/docs",
        redoc_url=None,
        openapi_url=None if config.production else "/api/openapi.json",
    )
    app.state.settings, app.state.repo, app.state.clock = config, repository, timer
    app.state.ai = ai_service or build_ai_service(config)
    errors(app)
    app.add_middleware(HandleUnexpected)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(SecurityMiddleware, settings=config)
    for module in (
        auth,
        catalog,
        bookings,
        projects,
        approvals,
        conflicts,
        analytics,
        ai,
        notifications,
        admin,
        health,
    ):
        app.include_router(module.router, prefix="/api")
    bundled = Path(__file__).resolve().parent / "static"
    built = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    mount_spa(app, static_dir or (bundled if bundled.is_dir() else built))
    return app


app = create_app()
