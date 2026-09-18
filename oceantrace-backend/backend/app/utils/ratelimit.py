"""
Minimal in-memory sliding-window rate limiter for auth endpoints.

Good enough for a single-process demo/hackathon deployment. For real
multi-instance production use, back this with Redis (e.g. via slowapi +
a Redis storage backend) instead of a process-local dict.
"""
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException

_hits = defaultdict(list)
_lock = Lock()


def rate_limit(key: str, spec: str):
    """spec like '10/minute' or '5/second'."""
    count_str, _, unit = spec.partition("/")
    limit = int(count_str)
    window_s = {"second": 1, "minute": 60, "hour": 3600}.get(unit, 60)
    now = time.time()
    with _lock:
        window = _hits[key]
        cutoff = now - window_s
        while window and window[0] < cutoff:
            window.pop(0)
        if len(window) >= limit:
            raise HTTPException(status_code=429, detail="Too many requests — please slow down.")
        window.append(now)
