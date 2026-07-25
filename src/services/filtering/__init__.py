"""Filtering sub-package — pre-fetch quality filtering of candidate URLs.

Current members:
    DomainQualityFilter  — drops low-quality domains and prioritises the
                            rest by authority tier, before PageFetcher.
"""

from .domain_filter import DomainQualityFilter

__all__ = [
    "DomainQualityFilter",
]
