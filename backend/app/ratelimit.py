"""In-memory sliding-window rate limiter. Single-replica deployment, so process-local
state is sufficient; `now` is injectable for testing."""

import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self, max_events: int, window_sec: int) -> None:
        self.max_events = max_events
        self.window_sec = window_sec
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        q = self._hits[key]
        cutoff = now - self.window_sec
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= self.max_events:
            return False
        q.append(now)
        return True

    def retry_after(self, key: str, now: float | None = None) -> int:
        now = time.time() if now is None else now
        q = self._hits.get(key)
        if not q:
            return 0
        return max(0, int(q[0] + self.window_sec - now))
