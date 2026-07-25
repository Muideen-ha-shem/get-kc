"""TTLCache — generic, thread-safe, time-to-live cache.

One shared, minimal in-memory cache implementation used everywhere caching
is needed in this pipeline — ``SearchManager`` (rewritten queries, search
results, fetched pages) and ``SemanticReranker`` (chunk embeddings) each get
their own *instance*, keyed independently, rather than each hand-rolling a
bespoke cache. This is per-process, in-memory only: it avoids redundant API
calls within a single running instance's uptime (the same question asked
twice, the same live page fetched for two different questions in the same
session) — it is not a distributed or persistent cache.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Generic, TypeVar

from .logging import get_logger

logger: logging.Logger = get_logger(__name__)

_MISSING = object()

K = TypeVar("K")
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    """A thread-safe cache with per-entry expiry and an optional size cap.

    Args:
        ttl_seconds: How long an entry stays valid after being set.
        maxsize: Maximum number of entries. When exceeded, the
            oldest-inserted entry is evicted (simple FIFO, not strict LRU —
            kept intentionally simple). ``None`` disables the cap.

    Typical usage::

        cache = TTLCache[str, str](ttl_seconds=300, maxsize=256)
        cache.set("key", "value")
        cache.get("key")  # -> "value" (until it expires or is evicted)
        cache.get("missing", "default")  # -> "default"
    """

    def __init__(self, *, ttl_seconds: float = 300.0, maxsize: int | None = 512) -> None:
        self._ttl = ttl_seconds
        self._maxsize = maxsize
        self._lock = threading.Lock()
        self._store: dict[K, tuple[float, V]] = {}
        self._order: list[K] = []
        self._hits = 0
        self._misses = 0

        logger.info("TTLCache ready (ttl_seconds=%.1f, maxsize=%s).", ttl_seconds, maxsize)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: K, default: V | None = None) -> V | None:
        """Return the cached value for *key*, or *default* if missing/expired."""
        with self._lock:
            entry = self._store.get(key, _MISSING)
            if entry is _MISSING:
                self._misses += 1
                return default

            expires_at, value = entry
            if expires_at < time.monotonic():
                self._evict_locked(key)
                self._misses += 1
                return default

            self._hits += 1
            return value

    def set(self, key: K, value: V) -> None:
        """Store *value* under *key*, resetting its TTL."""
        with self._lock:
            if key not in self._store:
                self._order.append(key)
                if self._maxsize is not None and len(self._order) > self._maxsize:
                    oldest = self._order.pop(0)
                    self._store.pop(oldest, None)
            self._store[key] = (time.monotonic() + self._ttl, value)

    def __contains__(self, key: K) -> bool:
        return self.get(key, _MISSING) is not _MISSING  # type: ignore[comparison-overlap]

    def clear(self) -> None:
        """Remove all entries and reset hit/miss counters."""
        with self._lock:
            self._store.clear()
            self._order.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict[str, int]:
        """Return ``{"hits", "misses", "size"}`` for observability/benchmarking."""
        with self._lock:
            return {"hits": self._hits, "misses": self._misses, "size": len(self._store)}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _evict_locked(self, key: K) -> None:
        """Remove *key*. Caller must already hold ``self._lock``."""
        self._store.pop(key, None)
        try:
            self._order.remove(key)
        except ValueError:
            pass
