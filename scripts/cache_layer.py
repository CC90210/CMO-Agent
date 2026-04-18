"""
TTL-based caching layer for Meta and Google Ads API responses.
==============================================================
File-based cache stored as JSON in data/cache/. Each cache entry is a
separate .json file containing the value and an expiry timestamp.

Standalone usage:
    python scripts/cache_layer.py

Import usage:
    from scripts.cache_layer import CacheLayer, cached

    cache = CacheLayer()

    # Manual get/set
    cache.set("my_key", {"data": 123}, ttl_seconds=300)
    value = cache.get("my_key")

    # Fetch-or-cache pattern
    result = cache.get_or_fetch("campaigns", engine.get_all_campaigns, ttl_seconds=120)

    # Decorator
    @cached(ttl_seconds=600)
    def expensive_call():
        ...
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("cache_layer")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CACHE_DIR = _PROJECT_ROOT / "data" / "cache"
_DEFAULT_TTL = 300  # seconds

# ---------------------------------------------------------------------------
# Credential loading (mirrors meta_ads_engine.py pattern)
# ---------------------------------------------------------------------------


def _load_env_agents() -> dict[str, str]:
    """
    Parse KEY=VALUE pairs from .env.agents at the project root.
    Skips blank lines and comment lines.
    """
    env_path = _PROJECT_ROOT / ".env.agents"
    if not env_path.exists():
        raise FileNotFoundError(
            f".env.agents not found at {env_path}. "
            "Copy .env.agents.template and fill in your credentials."
        )
    creds: dict[str, str] = {}
    with env_path.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            creds[key.strip()] = value.strip()
    return creds


# ---------------------------------------------------------------------------
# CacheLayer
# ---------------------------------------------------------------------------

_F = TypeVar("_F", bound=Callable[..., Any])


class CacheLayer:
    """
    File-based TTL cache for API responses.

    Each key maps to one JSON file in data/cache/ named by a sanitised hash
    of the key string. The file contains:
        {
            "key": "<original key>",
            "expires_at": "<ISO timestamp>",
            "value": <any JSON-serialisable object>
        }
    """

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        """
        Args:
            cache_dir: Override the default cache directory (data/cache/).
                       Primarily useful for tests.
        """
        self.cache_dir: Path = cache_dir or _CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        log.info("CacheLayer ready — dir: %s", self.cache_dir)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _key_to_path(self, key: str) -> Path:
        """Convert a cache key to a filesystem path using an MD5 hash."""
        safe_name = hashlib.md5(key.encode("utf-8")).hexdigest()  # noqa: S324 — non-crypto use
        return self.cache_dir / f"{safe_name}.json"

    def _now_ts(self) -> float:
        """Return the current UTC time as a Unix timestamp."""
        return datetime.now(timezone.utc).timestamp()

    def _read_entry(self, path: Path) -> Optional[dict]:
        """
        Read and deserialise a cache file.
        Returns None if the file does not exist or is malformed.
        """
        if not path.exists():
            return None
        try:
            with path.open(encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Cache read error for %s: %s", path.name, exc)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        """
        Return the cached value for key if it exists and has not expired.

        Args:
            key: Cache key string.

        Returns:
            Cached value, or None if not found / expired.
        """
        path = self._key_to_path(key)
        entry = self._read_entry(path)

        if entry is None:
            log.debug("Cache MISS: %s", key)
            return None

        expires_at = entry.get("expires_at", 0)
        if self._now_ts() > float(expires_at):
            log.debug("Cache EXPIRED: %s", key)
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None

        log.debug("Cache HIT: %s", key)
        return entry.get("value")

    def set(self, key: str, value: Any, ttl_seconds: int = _DEFAULT_TTL) -> None:
        """
        Store value under key with a TTL.

        Args:
            key:         Cache key string.
            value:       Any JSON-serialisable value.
            ttl_seconds: Time-to-live in seconds. Default 300.
        """
        expires_at = self._now_ts() + ttl_seconds
        entry = {
            "key": key,
            "expires_at": expires_at,
            "value": value,
        }
        path = self._key_to_path(key)
        try:
            with path.open("w", encoding="utf-8") as fh:
                json.dump(entry, fh, indent=2, default=str)
            log.debug("Cache SET: %s (TTL %ds)", key, ttl_seconds)
        except (OSError, TypeError) as exc:
            log.warning("Cache SET failed for key '%s': %s", key, exc)

    def invalidate(self, key: str) -> bool:
        """
        Remove a specific cache entry.

        Args:
            key: Cache key string.

        Returns:
            True if the entry existed and was removed, False otherwise.
        """
        path = self._key_to_path(key)
        if path.exists():
            try:
                path.unlink()
                log.info("Cache invalidated: %s", key)
                return True
            except OSError as exc:
                log.warning("Cache invalidate failed for '%s': %s", key, exc)
        return False

    def invalidate_all(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries removed.
        """
        removed = 0
        for json_file in self.cache_dir.glob("*.json"):
            try:
                json_file.unlink()
                removed += 1
            except OSError as exc:
                log.warning("Could not delete cache file %s: %s", json_file.name, exc)
        log.info("Cache cleared — %d entry/entries removed.", removed)
        return removed

    def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable[[], Any],
        ttl_seconds: int = _DEFAULT_TTL,
    ) -> Any:
        """
        Return cached value for key, or call fetch_fn, cache, and return.

        Args:
            key:         Cache key string.
            fetch_fn:    Zero-argument callable that returns the fresh value.
            ttl_seconds: TTL applied when caching a fresh result.

        Returns:
            Cached or freshly fetched value.
        """
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value

        log.info("Cache miss — fetching fresh value for key: %s", key)
        fresh_value = fetch_fn()
        self.set(key, fresh_value, ttl_seconds=ttl_seconds)
        return fresh_value

    def stats(self) -> dict:
        """
        Return basic cache statistics.

        Returns:
            dict with total_entries, expired_entries, valid_entries, cache_dir.
        """
        now = self._now_ts()
        total = 0
        expired = 0

        for json_file in self.cache_dir.glob("*.json"):
            total += 1
            entry = self._read_entry(json_file)
            if entry is None:
                expired += 1
                continue
            if now > float(entry.get("expires_at", 0)):
                expired += 1

        return {
            "total_entries": total,
            "expired_entries": expired,
            "valid_entries": total - expired,
            "cache_dir": str(self.cache_dir),
        }


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def cached(ttl_seconds: int = _DEFAULT_TTL) -> Callable[[_F], _F]:
    """
    Decorator to cache function results using a shared CacheLayer instance.

    The cache key is derived from the function's qualified name and the
    string representation of the call arguments.

    Args:
        ttl_seconds: Cache TTL in seconds. Default 300.

    Example:
        @cached(ttl_seconds=600)
        def get_campaigns():
            return engine.get_all_campaigns()
    """
    _shared_cache = CacheLayer()

    def decorator(fn: _F) -> _F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key_parts = [fn.__qualname__, repr(args), repr(sorted(kwargs.items()))]
            cache_key = "|".join(key_parts)
            return _shared_cache.get_or_fetch(
                cache_key,
                lambda: fn(*args, **kwargs),
                ttl_seconds=ttl_seconds,
            )

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------


def _run_demo() -> None:
    """Basic demo: set, get, stats, invalidate_all."""
    cache = CacheLayer()

    print()
    print("=" * 50)
    print("  CacheLayer Demo")
    print("=" * 50)

    cache.set("demo_key_1", {"campaigns": 5, "active": 3}, ttl_seconds=60)
    cache.set("demo_key_2", [1, 2, 3], ttl_seconds=3600)

    val1 = cache.get("demo_key_1")
    val2 = cache.get("demo_key_2")
    val_miss = cache.get("nonexistent_key")

    print(f"  demo_key_1   : {val1}")
    print(f"  demo_key_2   : {val2}")
    print(f"  nonexistent  : {val_miss}")

    stats = cache.stats()
    print(f"  Stats        : {stats}")

    removed = cache.invalidate_all()
    print(f"  Cleared {removed} entry/entries.")
    print("=" * 50)
    print()


if __name__ == "__main__":
    _run_demo()
