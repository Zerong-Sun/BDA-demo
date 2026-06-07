from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security headers to every response.

    Covers the common OWASP secure-header set (clickjacking, MIME sniffing,
    referrer leakage, transport security). The CSP is intentionally permissive
    for the API surface; the SPA is served by nginx which sets its own policy.
    """

    def __init__(self, app, *, hsts: bool = False):
        super().__init__(app)
        self._hsts = hsts

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-XSS-Protection", "0")
        response.headers.setdefault(
            "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
        )
        if self._hsts:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-process sliding-window rate limiter keyed by client IP.

    This is a single-instance guard suitable for the demo deployment. A
    horizontally scaled production setup should move this to a shared store
    (e.g. Redis) so limits are enforced across replicas.
    """

    def __init__(
        self,
        app,
        *,
        default_per_minute: int,
        auth_per_minute: int,
        auth_path_prefixes: tuple[str, ...] = ("/api/v1/auth/login",),
    ):
        super().__init__(app)
        self._default = default_per_minute
        self._auth = auth_per_minute
        self._auth_prefixes = auth_path_prefixes
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _limit_for(self, path: str) -> int:
        if any(path.startswith(prefix) for prefix in self._auth_prefixes):
            return self._auth
        return self._default

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not path.startswith("/api/v1"):
            return await call_next(request)

        limit = self._limit_for(path)
        bucket_key = f"{self._client_ip(request)}:{'auth' if limit == self._auth else 'default'}"
        now = time.monotonic()
        window_start = now - 60.0

        hits = self._hits[bucket_key]
        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= limit:
            retry_after = max(1, int(60 - (now - hits[0])))
            return JSONResponse(
                status_code=429,
                content={
                    "error_code": "rate_limited",
                    "message": "Too many requests. Please slow down.",
                    "details": {"path": path, "limit_per_minute": limit},
                    "retryable": True,
                },
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
        return await call_next(request)
