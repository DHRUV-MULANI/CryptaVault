"""Rate limiting and Request-ID tracing middleware."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding window rate limiter per client IP."""

    def __init__(
        self, app, requests_per_minute: int = 120, auth_requests_per_minute: int = 30
    ) -> None:
        super().__init__(app)
        self.rpm = requests_per_minute
        self.auth_rpm = auth_requests_per_minute
        self._history: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        client_ip = request.client.host if request.client else "127.0.0.1"

        is_auth = request.url.path.startswith("/api/auth")
        max_allowed = self.auth_rpm if is_auth else self.rpm

        now = time.time()
        window_start = now - 60.0

        # Purge timestamps older than 60s
        timestamps = [t for t in self._history[client_ip] if t > window_start]
        self._history[client_ip] = timestamps

        if len(timestamps) >= max_allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Try again later.",
                    "request_id": request_id,
                },
                headers={
                    "X-Request-ID": request_id,
                    "Retry-After": "60",
                },
            )

        self._history[client_ip].append(now)

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-RateLimit-Remaining"] = str(max_allowed - len(self._history[client_ip]))
        return response
