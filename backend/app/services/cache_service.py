"""
Simple in-memory TTL cache for heavy analytics queries.
Keys expire after ttl_seconds (default 60).
Thread-safety is not required for this single-process FastAPI deployment.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

_cache: dict = {}


def get_cache(key: str) -> Optional[Any]:
    """Return cached value if it exists and has not expired; otherwise None."""
    entry = _cache.get(key)
    if entry is None:
        return None
    if datetime.now(timezone.utc) > entry["expires_at"]:
        del _cache[key]
        return None
    return entry["value"]


def set_cache(key: str, value: Any, ttl_seconds: int = 60) -> None:
    """Store value under key with an expiry of ttl_seconds from now."""
    _cache[key] = {
        "value": value,
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
    }


def clear_cache(key: Optional[str] = None) -> None:
    """Remove a single key or flush the entire cache."""
    if key is not None:
        _cache.pop(key, None)
    else:
        _cache.clear()


def cache_size() -> int:
    """Return number of entries currently in the cache (including expired)."""
    return len(_cache)
