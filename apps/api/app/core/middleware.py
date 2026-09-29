"""ASGI middleware: request id + request logging, and security headers.

Implemented as pure ASGI middleware (not ``BaseHTTPMiddleware``) so streaming responses and
WebSockets are unaffected.
"""

from __future__ import annotations

import time
from collections.abc import MutableMapping

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.request_id import REQUEST_ID_HEADER, normalise_request_id

log = structlog.get_logger("app.request")

SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site",
    "Permissions-Policy": "geolocation=(self), camera=(), microphone=(), payment=()",
    "Cache-Control": "no-store",
}


class RequestContextMiddleware:
    """Assign a request id, bind it to the log context, and emit one access log per request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = normalise_request_id(headers.get(REQUEST_ID_HEADER))
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        started = time.perf_counter()
        status_code: int | None = None

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            if scope["type"] == "http":
                request = Request(scope)
                route = scope.get("route")
                log.info(
                    "http_request",
                    method=request.method,
                    # Route template, not the raw path, so ids never end up in logs.
                    path=getattr(route, "path", request.url.path),
                    status=status_code,
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                )
            structlog.contextvars.clear_contextvars()


class SecurityHeadersMiddleware:
    """Attach baseline security headers to every HTTP response (security.md §6)."""

    def __init__(self, app: ASGIApp, headers: MutableMapping[str, str] | None = None) -> None:
        self.app = app
        self.headers = dict(headers or SECURITY_HEADERS)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                for name, value in self.headers.items():
                    if name not in response_headers:
                        response_headers.append(name, value)
            await send(message)

        await self.app(scope, receive, send_with_headers)
