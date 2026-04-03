"""Simple in-memory TTL cache for Firefly III API responses."""
import time
import threading
from typing import Any, Optional


class TTLCache:
    """Thread-safe TTL cache with configurable default expiry."""

    def __init__(self, default_ttl: int = 60):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Return cached value if not expired, else None."""
        with self._lock:
            if key not in self._cache:
                return None
            value, expiry = self._cache[key]
            if time.monotonic() > expiry:
                del self._cache[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value with TTL (seconds). Uses default_ttl if not specified."""
        expiry = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
        with self._lock:
            self._cache[key] = (value, expiry)

    def invalidate(self, key: str) -> None:
        """Remove a specific key from cache."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Remove all cached entries."""
        with self._lock:
            self._cache.clear()


# Module-level singleton
cache = TTLCache(default_ttl=60)
