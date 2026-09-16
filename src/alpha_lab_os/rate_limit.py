from __future__ import annotations

import threading
import time
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, rate_per_second: float, window_seconds: float = 1.0):
        self.rate = float(rate_per_second)
        self.window = float(window_seconds)
        self._events: deque[float] = deque()
        self._lock = threading.Lock()

    def wait(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                while self._events and now - self._events[0] >= self.window:
                    self._events.popleft()
                if len(self._events) < max(1, int(self.rate * self.window)):
                    self._events.append(now)
                    return
                delay = self.window - (now - self._events[0])
            time.sleep(max(0.001, delay))

