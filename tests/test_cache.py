"""Tests for the shared TTLCache utility."""

from __future__ import annotations

import threading
import time

from src.shared.cache import TTLCache


# ---------------------------------------------------------------------------
# Basic get/set
# ---------------------------------------------------------------------------


class TestTTLCacheBasics:
    def test_set_then_get_returns_value(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_missing_key_returns_default(self):
        cache = TTLCache(ttl_seconds=60)
        assert cache.get("missing") is None
        assert cache.get("missing", "fallback") == "fallback"

    def test_contains_reflects_presence(self):
        cache = TTLCache(ttl_seconds=60)
        assert "key" not in cache
        cache.set("key", "value")
        assert "key" in cache

    def test_overwrite_updates_value(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("key", "first")
        cache.set("key", "second")
        assert cache.get("key") == "second"

    def test_clear_removes_all_entries(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.stats()["size"] == 0


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------


class TestTTLCacheExpiry:
    def test_entry_expires_after_ttl(self):
        cache = TTLCache(ttl_seconds=0.05)
        cache.set("key", "value")
        assert cache.get("key") == "value"
        time.sleep(0.1)
        assert cache.get("key") is None

    def test_expired_entry_removed_from_size(self):
        cache = TTLCache(ttl_seconds=0.05)
        cache.set("key", "value")
        time.sleep(0.1)
        cache.get("key")  # triggers lazy eviction
        assert cache.stats()["size"] == 0

    def test_long_ttl_survives(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("key", "value")
        time.sleep(0.05)
        assert cache.get("key") == "value"


# ---------------------------------------------------------------------------
# Size cap / eviction
# ---------------------------------------------------------------------------


class TestTTLCacheEviction:
    def test_maxsize_evicts_oldest(self):
        cache = TTLCache(ttl_seconds=60, maxsize=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # should evict "a"
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_none_maxsize_never_evicts(self):
        cache = TTLCache(ttl_seconds=60, maxsize=None)
        for i in range(50):
            cache.set(f"key{i}", i)
        assert cache.stats()["size"] == 50

    def test_updating_existing_key_does_not_count_toward_maxsize(self):
        cache = TTLCache(ttl_seconds=60, maxsize=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("a", 100)  # update, not a new insertion
        assert cache.get("a") == 100
        assert cache.get("b") == 2


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class TestTTLCacheStats:
    def test_hits_and_misses_tracked(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("key", "value")
        cache.get("key")
        cache.get("key")
        cache.get("missing")
        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1

    def test_clear_resets_stats(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("key", "value")
        cache.get("key")
        cache.get("missing")
        cache.clear()
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestTTLCacheThreadSafety:
    def test_concurrent_set_and_get_does_not_crash_or_corrupt(self):
        cache = TTLCache(ttl_seconds=60, maxsize=1000)
        errors = []

        def worker(n):
            try:
                for i in range(200):
                    cache.set(f"k{n}-{i}", i)
                    cache.get(f"k{n}-{i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
