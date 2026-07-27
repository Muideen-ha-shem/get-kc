"""Advisory sub-package (Phase 19) — turns HavisIQ from a grounded Q&A
pipeline into a business advisor, without touching the retrieval pipeline
it sits on top of.

Members:
    BusinessIntentEngine, BusinessIntent — understands *why* a customer is
        asking (wraps ProductRouter, enriches with registry context).
    RecommendationEngine, Recommendation — ranked, grounded product
        recommendations; never recommends a product without registry +
        retrieval-evidence support.
    ClarificationEngine — asks instead of guessing on genuine ambiguity.
    NextActionsEngine, NextAction — contextual next-step suggestions.
    AdvisoryResponseLayer, AdvisoryResult — orchestrates the above for
        ChatOrchestrator; optional, purely additive.
    SessionContext, SessionState — session-scoped conversation awareness
        (in-memory only; not yet wired into the live /chat endpoint).
    AnalyticsService — optional, in-memory, anonymous usage counters.
"""

from .advisory_layer import AdvisoryResponseLayer, AdvisoryResult
from .analytics_service import AnalyticsService
from .clarification_engine import ClarificationEngine
from .intent_engine import BusinessIntent, BusinessIntentEngine
from .next_actions import NextAction, NextActionsEngine
from .recommendation_engine import Recommendation, RecommendationEngine
from .session_context import SessionContext, SessionState

__all__ = [
    "AdvisoryResponseLayer",
    "AdvisoryResult",
    "AnalyticsService",
    "ClarificationEngine",
    "BusinessIntent",
    "BusinessIntentEngine",
    "NextAction",
    "NextActionsEngine",
    "Recommendation",
    "RecommendationEngine",
    "SessionContext",
    "SessionState",
]
