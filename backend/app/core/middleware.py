import json
import logging
from collections import deque
from threading import Lock
from time import monotonic
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .config import Settings
from .security import token_user

LOG = logging.getLogger("lablink")
MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
BODY_LIMIT = 65536


def error_data(code: str, message: str, request_id: str, details: object = None) -> dict:
    """Build the standard JSON error envelope."""
    return {"error": {"code": code, "message": message, "details": details or {}, "request_id": request_id}}


def replay_body(raw: bytes, receive: Receive) -> Receive:
    """Replay the validated body once, then forward ASGI receive events."""
    pending = True

    async def buffered() -> Message:
        nonlocal pending
        if pending:
            pending = False
            return {"type": "http.request", "body": raw, "more_body": False}
        return await receive()

    return buffered


class Limiter:
    """Track rate limit windows by action and subject."""

    def __init__(self) -> None:
        self.events: dict[tuple[str, str, int], deque[float]] = {}
        self.lock = Lock()
        self.last_cleanup = 0.0

    def allow(self, name: str, subject: str, rules: list[tuple[int, int]]) -> int:
        """Record an allowed operation or return the retry delay in seconds."""
        now = monotonic()
        with self.lock:
            if now - self.last_cleanup > 60:
                self.events = {k: q for k, q in self.events.items() if q and q[-1] > now - k[2]}
                self.last_cleanup = now
            queues = []
            for limit, seconds in rules:
                queue = self.events.setdefault((name, subject, seconds), deque())
                while queue and queue[0] <= now - seconds:
                    queue.popleft()
                if len(queue) >= limit:
                    return max(1, int(queue[0] + seconds - now) + 1)
                queues.append(queue)
            for queue in queues:
                queue.append(now)
        return 0


class SecurityMiddleware:
    """Apply request limits, response headers, and structured logging."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app, self.settings, self.limiter = app, settings, Limiter()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        path, method = scope["path"], scope["method"]
        api = path.startswith("/api/")
        status, start = 500, monotonic()

        async def with_headers(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                self.headers(MutableHeaders(scope=message), request_id, api)
            await send(message)

        try:
            if api:
                rejection = self.check_api_request(scope, request_id)
                if rejection is not None:
                    await rejection(scope, receive, with_headers)
                    return
                if method in MUTATING:
                    raw = await self.body(receive)
                    if raw is None:
                        rejection = JSONResponse(
                            error_data("BODY_TOO_LARGE", "Request bodies are limited to 64 KB.", request_id),
                            status_code=413,
                        )
                        await rejection(scope, receive, with_headers)
                        return
                    receive = replay_body(raw, receive)
            await self.app(scope, receive, with_headers)
        finally:
            LOG.info(
                json.dumps(
                    {
                        "severity": "INFO",
                        "message": "http_request",
                        "request_id": request_id,
                        "path": path,
                        "status": status,
                        "latency_ms": round((monotonic() - start) * 1000, 1),
                    }
                )
            )

    def check_api_request(self, scope: Scope, request_id: str) -> JSONResponse | None:
        """Check the CSRF marker before charging the request to a rate limit."""
        headers = Headers(scope=scope)
        method = scope["method"]
        if method in MUTATING and headers.get("x-requested-with") != "LabLink":
            return JSONResponse(
                error_data("CSRF_CHECK_FAILED", "The request could not be verified.", request_id),
                status_code=403,
            )
        retry = self.rate(scope, headers, scope["path"], method)
        if retry:
            return JSONResponse(
                error_data("RATE_LIMITED", "Too many requests. Please try again shortly.", request_id),
                status_code=429,
                headers={"Retry-After": str(retry)},
            )
        return None

    async def body(self, receive: Receive) -> bytes | None:
        """Buffer a request body up to the configured byte limit."""
        data = bytearray()
        while True:
            chunk = await receive()
            if chunk["type"] == "http.disconnect":
                return bytes(data)
            data.extend(chunk.get("body", b""))
            if len(data) > BODY_LIMIT:
                return None
            if not chunk.get("more_body", False):
                return bytes(data)

    def rate(self, scope: Scope, headers: Headers, path: str, method: str) -> int:
        """Return the retry delay for a rate-limited API operation."""
        if path in {"/api/auth/personas", "/api/auth/demo", "/api/auth/logout"}:
            return self.limiter.allow("auth", (scope.get("client") or ("unknown",))[0], [(10, 60)])
        if method not in MUTATING and not path.endswith("/summary"):
            return 0
        cookies = dict(part.strip().split("=", 1) for part in headers.get("cookie", "").split(";") if "=" in part)
        subject = token_user(self.settings, cookies.get("ll_session")) or (scope.get("client") or ("unknown",))[0]
        if path.startswith("/api/ai/") or path.endswith(("/recommend", "/summary")):
            return self.limiter.allow("ai", subject, [(10, 60), (100, 86400)])
        return self.limiter.allow("write", subject, [(60, 60)])

    def headers(self, headers: MutableHeaders, request_id: str, api: bool) -> None:
        """Attach security, cache, and request tracing headers."""
        csp = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
            "connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        headers["Content-Security-Policy"] = csp + ("; upgrade-insecure-requests" if self.settings.production else "")
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        headers["Cross-Origin-Opener-Policy"] = "same-origin"
        headers["X-Request-ID"] = request_id
        if self.settings.production:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if api:
            headers["Cache-Control"] = "no-store"
