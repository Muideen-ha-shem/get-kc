"""AnalyticsService — optional, in-memory, anonymous usage counters.

No PII, no persistence, no database — process-lifetime counters only, in
the same spirit as everything else in the advisory layer that stays
in-memory-only per this phase's constraints. Entirely optional: every
recording method is safe to call on a ``None`` service via the module-level
``record_safely`` helper, so callers (``ChatOrchestrator``) never need an
``if analytics:`` guard scattered through their code, and a failure here
can never break a chat response.
"""

from __future__ import annotations

import logging
import threading
from collections import Counter
from typing import Any

from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)


class AnalyticsService:
    """Thread-safe, in-memory counters for advisory-layer usage events."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._recommended: Counter[str] = Counter()
        self._accepted: Counter[str] = Counter()
        self._business_problems: Counter[str] = Counter()
        self._compared_pairs: Counter[tuple[str, ...]] = Counter()
        self._demo_ctas: Counter[str] = Counter()
        self._custom_software_requests = 0
        logger.info("AnalyticsService ready.")

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_recommendation(self, product: str) -> None:
        with self._lock:
            self._recommended[product] += 1

    def record_accepted_recommendation(self, product: str) -> None:
        with self._lock:
            self._accepted[product] += 1

    def record_business_problem(self, label: str) -> None:
        with self._lock:
            self._business_problems[label] += 1

    def record_comparison(self, products: list[str]) -> None:
        if len(products) < 2:
            return
        with self._lock:
            self._compared_pairs[tuple(sorted(products))] += 1

    def record_demo_cta(self, product: str) -> None:
        with self._lock:
            self._demo_ctas[product] += 1

    def record_custom_software_request(self) -> None:
        with self._lock:
            self._custom_software_requests += 1

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def top_recommended(self, n: int = 5) -> list[tuple[str, int]]:
        with self._lock:
            return self._recommended.most_common(n)

    def top_business_problems(self, n: int = 5) -> list[tuple[str, int]]:
        with self._lock:
            return self._business_problems.most_common(n)

    def top_compared(self, n: int = 5) -> list[tuple[tuple[str, ...], int]]:
        with self._lock:
            return self._compared_pairs.most_common(n)

    def demo_cta_count(self, product: str | None = None) -> int:
        with self._lock:
            if product is None:
                return sum(self._demo_ctas.values())
            return self._demo_ctas.get(product, 0)

    def custom_software_request_count(self) -> int:
        with self._lock:
            return self._custom_software_requests

    def snapshot(self) -> dict[str, Any]:
        """A single dict of every metric — convenient for an admin/debug
        endpoint in a future phase, or for tests."""
        with self._lock:
            return {
                "top_recommended": self._recommended.most_common(),
                "top_accepted": self._accepted.most_common(),
                "top_business_problems": self._business_problems.most_common(),
                "top_compared": self._compared_pairs.most_common(),
                "demo_ctas": dict(self._demo_ctas),
                "custom_software_requests": self._custom_software_requests,
            }


def record_safely(analytics: AnalyticsService | None, method_name: str, *args: Any) -> None:
    """Call ``analytics.<method_name>(*args)`` if *analytics* is configured,
    swallowing any error — analytics must never break a chat response."""
    if analytics is None:
        return
    try:
        getattr(analytics, method_name)(*args)
    except Exception as exc:
        logger.warning("AnalyticsService: %s(%r) failed — %s.", method_name, args, exc)
