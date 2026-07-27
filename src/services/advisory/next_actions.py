"""NextActionsEngine — generates contextual next-step suggestions.

Actions are computed deterministically from recommendation context, never
hardcoded into a response template:

* Discussing one or more recommended products -> Learn More / Compare
  Solutions (when there's more than one candidate) / Request Demo / Talk to
  an Expert.
* No product matched, but the question is about a Ha-Shem *service* area
  that doesn't have its own product registry entry (Cybersecurity, Cloud,
  Managed Services, Training, ...) -> Contact Sales / Talk to an Expert.
* The question is about custom/bespoke software -> Build a Custom Solution.
* Anything else (fully generic question) -> no actions.

The service-area and custom-software keyword lists here are deliberately
separate from ``PRODUCT_REGISTRY`` — Phase 18 kept those categories
frontend-only (advisory listings with no crawled site, nothing to
retrieve), so there is no backend registry entry to reuse for them; this
is genuinely the only place that intent exists server-side, not a
duplicate of something that already lives elsewhere.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from ...shared.logging import get_logger
from .intent_engine import BusinessIntent
from .recommendation_engine import Recommendation

logger: logging.Logger = get_logger(__name__)

_CUSTOM_SOFTWARE_KEYWORDS = (
    "custom software", "custom solution", "custom-built", "software built for",
    "build software", "bespoke software", "build us software", "software specifically for",
)

_ADVISORY_SERVICE_KEYWORDS = (
    "cybersecurity", "cyber security", "cloud migration", "cloud services",
    "software development", "managed services", "training", "certification program",
)


@dataclass(frozen=True)
class NextAction:
    label: str
    action_type: str
    target: str | None = None


class NextActionsEngine:
    """Generates the next-step suggestions attached to a chat response."""

    def generate(
        self,
        intent: BusinessIntent,
        recommendations: Sequence[Recommendation] | None = None,
    ) -> list[NextAction]:
        question = (intent.question or "").lower()
        recommendations = recommendations or []

        if any(keyword in question for keyword in _CUSTOM_SOFTWARE_KEYWORDS):
            return [NextAction("Build a Custom Solution", "custom_solution")]

        if recommendations:
            primary = recommendations[0]
            actions = [NextAction(f"Learn more about {primary.product}", "learn_more", primary.product)]
            if len(recommendations) > 1 or primary.alternatives or primary.related:
                actions.append(NextAction("Compare Solutions", "compare", primary.product))
            actions.append(NextAction(f"Request a {primary.product} Demo", "request_demo", primary.product))
            actions.append(NextAction("Talk to an Expert", "talk_to_expert"))
            return actions

        if any(keyword in question for keyword in _ADVISORY_SERVICE_KEYWORDS):
            return [
                NextAction("Contact Sales", "contact_sales"),
                NextAction("Talk to an Expert", "talk_to_expert"),
            ]

        return []
