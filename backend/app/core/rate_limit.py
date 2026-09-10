"""Lightweight in-memory rate limiter (no extra dependencies).

Protects auth endpoints from brute force. Simple sliding-window counter per
(scope, key). In multi-worker production use Redis; this is sufficient for
single-process and demo deployments.
"""
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException, Request

_lock = threading.Lock()
_hits: dict[str, list[float]] = defaultdict(list)


def rate_limit(scope: str, limit: int, window_seconds: int = 300):
    """Dependency factory returning a FastAPI dependency that enforces the limit.

    Usage:
        @router.post("/login", dependencies=[Depends(rate_limit("login", 10, 300))])
    """

    def dependency(request: Request):
        key = request.client.host if request.client else "unknown"
        ident = f"{scope}:{key}"
        now = time.time()
        with _lock:
            recent = _hits[ident]
            # drop entries outside the window
            while recent and now - recent[0] > window_seconds:
                recent.pop(0)
            if len(recent) >= limit:
                raise HTTPException(
                    status_code=429,
                    detail="Too many attempts. Please try again later.",
                    headers={"Retry-After": str(int(window_seconds))},
                )
            recent.append(now)

    return dependency


def reset_rate_limits() -> None:
    with _lock:
        _hits.clear()