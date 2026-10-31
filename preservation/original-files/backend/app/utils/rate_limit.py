"""Minimal in-process sliding-window limiter for auth endpoints.

Good enough for a single process. Behind multiple workers use Redis (docker-compose
ships one) -- swap the storage, keep the dependency interface.
"""
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

_hits: dict[str, deque] = defaultdict(deque)
_lock = Lock()


def reset_rate_limits() -> None:
    with _lock:
        _hits.clear()


def _client_key(request: Request) -> str:
    # Behind any proxy (Vite dev proxy, Docker, a reverse proxy) `request.client.host` is the
    # PROXY's address (e.g. 127.0.0.1) for every visitor, so the old key put all users in one
    # shared 10/minute bucket: a few attempts by anyone could lock everyone out with
    # "Too many attempts". Prefer the first X-Forwarded-For hop the proxy sends (Vite is
    # configured with `xfwd: true`; enable the equivalent on a production reverse proxy, which
    # must be the only thing able to reach the backend so clients can't spoof this header).
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        first = fwd.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def auth_rate_limit(request: Request) -> None:
    s = get_settings()
    if not s.RATE_LIMIT_ENABLED:
        return
    key = f"{_client_key(request)}:{request.url.path}"
    now = time.monotonic()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > s.AUTH_RATE_WINDOW_SECONDS:
            q.popleft()
        if len(q) >= s.AUTH_RATE_LIMIT:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Try again in a minute.")
        q.append(now)
