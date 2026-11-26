import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Thread-safe in-memory per-key sliding-window rate limiter.

    Note: Single-process only. Multi-instance deployments will need Redis.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                )
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def rate_limit_auth(request: Request) -> None:
    limiter: InMemoryRateLimiter | None = getattr(request.app.state, "auth_rate_limiter", None)
    if limiter is None:
        limiter = InMemoryRateLimiter()
        request.app.state.auth_rate_limiter = limiter
    client_ip = request.client.host if request.client else "unknown"
    limiter.check(f"auth:{client_ip}")
