"""EscalationService — orchestrates the escalation decision (or a direct,
already-decided escalation), builds the handoff summary, creates the
`escalations` row, and notifies available agents (Phase 24).

Notification reuses the existing ``NotificationService`` unmodified — the
"notify every available agent" loop lives here, not inside
``NotificationService`` (which stays a single-recipient, best-effort
primitive exactly as documented).
"""

from __future__ import annotations

import logging
from typing import Any

from ...shared.logging import get_logger
from ..advisory.advisory_layer import AdvisoryResult
from ..agents.agent_service import AgentService
from ..notifications.notification_service import NotificationService
from .decision import decide_escalation
from .department_routing import determine_department
from .escalation_models import Escalation
from .escalation_repository import EscalationRepository
from .intent import detect_critical_intent, detect_sentiment_hint
from .routing import select_best_agent
from .summary import build_summary

logger: logging.Logger = get_logger(__name__)


class EscalationService:
    def __init__(
        self,
        agent_service: AgentService | None = None,
        repository: EscalationRepository | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._agent_service = agent_service or AgentService()
        self._repository = repository or EscalationRepository()
        self._notification_service = notification_service or NotificationService()

    def escalate(
        self,
        *,
        workspace_id: str,
        workspace_name: str,
        conversation_id: str | None,
        question: str,
        kb_confidence: float | None,
        has_evidence: bool,
        advisory: AdvisoryResult | None,
        customer_company: str | None,
    ) -> Escalation | None:
        """Runs the escalation decision; writes nothing if it says no —
        this is the "never escalate by default" guarantee."""
        decision = decide_escalation(question=question, kb_confidence=kb_confidence, has_evidence=has_evidence)
        if not decision.should_escalate:
            return None
        return self._create_and_notify(
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            conversation_id=conversation_id,
            question=question,
            advisory=advisory,
            customer_company=customer_company,
            trigger_reason=decision.reason or "unresolved",
        )

    def create_direct(
        self,
        *,
        workspace_id: str,
        workspace_name: str,
        conversation_id: str | None,
        question: str,
        trigger_reason: str = "explicit_request",
        advisory: AdvisoryResult | None = None,
        customer_company: str | None = None,
    ) -> Escalation:
        """Skips the decision step entirely — used when the decision has
        already been made (the AI recommended it via /chat, or the user
        explicitly clicked "talk to a human")."""
        return self._create_and_notify(
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            conversation_id=conversation_id,
            question=question,
            advisory=advisory,
            customer_company=customer_company,
            trigger_reason=trigger_reason,
        )

    def _create_and_notify(
        self,
        *,
        workspace_id: str,
        workspace_name: str,
        conversation_id: str | None,
        question: str,
        advisory: AdvisoryResult | None,
        customer_company: str | None,
        trigger_reason: str,
    ) -> Escalation:
        sentiment = detect_sentiment_hint(question)
        summary: dict[str, Any] = build_summary(
            workspace_name=workspace_name,
            customer_company=customer_company,
            advisory=advisory,
            question=question,
            sentiment=sentiment,
        )
        critical_category = detect_critical_intent(question)
        department = determine_department(critical_category=critical_category, question=question)
        escalation = self._repository.create(workspace_id, conversation_id, trigger_reason, department, summary)

        available_agents = self._agent_service.list_available(workspace_id)

        # --- Auto-assignment (Phase 25): best available agent, not "first
        # available." Workload+idle-time ordering, soft department
        # preference. Falls back to leaving the escalation `waiting` (the
        # Phase 24 queue, still claimable via /agent/accept) when no agent
        # is available at all.
        workloads = {
            agent.id: self._repository.count_active_for_agent(agent.id) for agent in available_agents
        }
        best_agent = select_best_agent(available_agents, workloads, department=department)
        if best_agent is not None:
            escalation = self._repository.assign(escalation.id, best_agent.id)

        for agent in available_agents:
            self._notification_service.notify(
                agent.auth_user_id,
                "support_update",
                title="New escalation waiting",
                body=question[:200],
                workspace_id=workspace_id,
            )
        logger.info(
            "EscalationService: escalation %s created (reason=%s, department=%s), "
            "assigned=%s, notified %d available agent(s).",
            escalation.id,
            trigger_reason,
            department,
            best_agent.id if best_agent else None,
            len(available_agents),
        )
        return escalation
