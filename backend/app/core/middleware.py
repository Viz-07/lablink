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
    return {"error": {"code": code, "message": message, "details": details or {}, "request_id": request_id}}


class Limiter:
    def __init__(self) -> None:
        self.events: dict[tuple[str, str, int], deque[float]] = {}
        self.lock = Lock()
        self.last_cleanup = 0.0

    def allow(self, name: str, subject: str, rules: list[tuple[int, int]]) -> int:
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

        async def reject(code: str, message: str, response_status: int, retry: int = 0) -> None:
            response = JSONResponse(
                error_data(code, message, request_id),
                response_status,
                headers={"Retry-After": str(retry)} if retry else None,
            )
            await response(scope, receive, with_headers)

        try:
            if api:
                headers = Headers(scope=scope)
                if method in MUTATING and headers.get("x-requested-with") != "LabLink":
                    await reject("CSRF_CHECK_FAILED", "The request could not be verified.", 403)
                    return
                retry = self.rate(scope, headers, path, method)
                if retry:
                    await reject("RATE_LIMITED", "Too many requests. Please try again shortly.", 429, retry)
                    return
                if method in MUTATING:
                    raw = await self.body(receive)
                    if raw is None:
                        await reject("BODY_TOO_LARGE", "Request bodies are limited to 64 KB.", 413)
                        return
                    first = True

                    async def buffered() -> Message:
                        nonlocal first
                        if first:
                            first = False
                            return {"type": "http.request", "body": raw, "more_body": False}
                        return await receive()

                    await self.app(scope, buffered, with_headers)
                    return
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

    async def body(self, receive: Receive) -> bytes | None:
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
