"""Pure unit tests for decide_escalation — mirrors test_routing.py's style."""

from __future__ import annotations

from src.services.escalation.decision import decide_escalation


class TestDecideEscalation:
    def test_explicit_request_wins(self):
        decision = decide_escalation(question="I want to talk to a human", kb_confidence=0.9, has_evidence=True)
        assert decision.should_escalate is True
        assert decision.reason == "explicit_request"

    def test_critical_intent_when_no_explicit_request(self):
        decision = decide_escalation(question="I've been hacked, help!", kb_confidence=0.9, has_evidence=True)
        assert decision.should_escalate is True
        assert decision.reason == "critical_intent"
        assert decision.critical_category == "security_incident"

    def test_low_confidence_triggers_escalation(self):
        decision = decide_escalation(question="What is SPIDIFY?", kb_confidence=0.1, has_evidence=True)
        assert decision.should_escalate is True
        assert decision.reason == "low_confidence"

    def test_no_evidence_triggers_unresolved(self):
        decision = decide_escalation(question="What is SPIDIFY?", kb_confidence=None, has_evidence=False)
        assert decision.should_escalate is True
        assert decision.reason == "unresolved"

    def test_continues_when_confident_and_has_evidence(self):
        decision = decide_escalation(question="What is SPIDIFY?", kb_confidence=0.9, has_evidence=True)
        assert decision.should_escalate is False
        assert decision.reason is None

    def test_priority_explicit_request_over_critical_intent(self):
        decision = decide_escalation(
            question="I've been hacked, talk to a human now", kb_confidence=0.9, has_evidence=True
        )
        assert decision.reason == "explicit_request"

    def test_priority_critical_intent_over_low_confidence(self):
        decision = decide_escalation(question="I've been hacked", kb_confidence=0.1, has_evidence=True)
        assert decision.reason == "critical_intent"
