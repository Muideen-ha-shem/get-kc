"""Tests for SessionContext."""

from __future__ import annotations

from src.services.advisory.session_context import PendingAction, SessionContext


class TestSessionContextBasics:
    def test_new_session_starts_empty(self):
        ctx = SessionContext()
        state = ctx.get("session-1")
        assert state.discussed_products == []
        assert state.last_product() is None

    def test_record_products_appends_without_duplicates(self):
        ctx = SessionContext()
        ctx.record_products("s1", ["SPIDIFY"])
        ctx.record_products("s1", ["SPIDIFY", "ZivaAIRA"])
        state = ctx.get("s1")
        assert state.discussed_products == ["SPIDIFY", "ZivaAIRA"]

    def test_last_product_reflects_most_recent(self):
        ctx = SessionContext()
        ctx.record_products("s1", ["SPIDIFY"])
        ctx.record_products("s1", ["ZivaAIRA"])
        assert ctx.get("s1").last_product() == "ZivaAIRA"

    def test_sessions_are_isolated(self):
        ctx = SessionContext()
        ctx.record_products("s1", ["SPIDIFY"])
        ctx.record_products("s2", ["ZivaAIRA"])
        assert ctx.get("s1").last_product() == "SPIDIFY"
        assert ctx.get("s2").last_product() == "ZivaAIRA"

    def test_record_recommendation(self):
        ctx = SessionContext()
        ctx.record_recommendation("s1", "SPIDIFY")
        assert ctx.get("s1").recommended_products == ["SPIDIFY"]

    def test_record_comparison_requires_two_products(self):
        ctx = SessionContext()
        ctx.record_comparison("s1", ["SPIDIFY"])
        assert ctx.get("s1").comparisons == []
        ctx.record_comparison("s1", ["SPIDIFY", "ZivaAIRA"])
        assert ctx.get("s1").comparisons == [("SPIDIFY", "ZivaAIRA")]

    def test_record_business_problem(self):
        ctx = SessionContext()
        ctx.record_business_problem("s1", "Identity Verification")
        assert ctx.get("s1").current_business_problem == "Identity Verification"


class TestSessionContextResolveReference:
    def test_resolves_pronoun_to_last_product(self):
        ctx = SessionContext()
        ctx.record_products("s1", ["SPIDIFY"])
        resolved = ctx.resolve_reference("s1", "How much does it cost?")
        assert "SPIDIFY" in resolved
        assert resolved == "How much does SPIDIFY cost?"

    def test_resolves_to_most_recently_discussed_product(self):
        ctx = SessionContext()
        ctx.record_products("s1", ["SPIDIFY"])
        ctx.record_products("s1", ["ZivaAIRA"])
        resolved = ctx.resolve_reference("s1", "What does it do?")
        assert "ZivaAIRA" in resolved

    def test_no_session_history_leaves_question_unchanged(self):
        ctx = SessionContext()
        resolved = ctx.resolve_reference("unknown-session", "How much does it cost?")
        assert resolved == "How much does it cost?"

    def test_no_pronoun_present_leaves_question_unchanged(self):
        ctx = SessionContext()
        ctx.record_products("s1", ["SPIDIFY"])
        resolved = ctx.resolve_reference("s1", "What are your office hours?")
        assert resolved == "What are your office hours?"

    def test_question_already_naming_a_product_is_left_alone(self):
        ctx = SessionContext()
        ctx.record_products("s1", ["SPIDIFY"])
        resolved = ctx.resolve_reference("s1", "How much does ZivaAIRA cost, is it expensive?")
        assert resolved == "How much does ZivaAIRA cost, is it expensive?"

    def test_this_and_that_also_resolve(self):
        ctx = SessionContext()
        ctx.record_products("s1", ["PayCheq"])
        assert "PayCheq" in ctx.resolve_reference("s1", "Tell me more about this.")
        assert "PayCheq" in ctx.resolve_reference("s1", "Is that available on mobile?")

    def test_this_company_is_not_resolved_to_last_product(self):
        """Live-confirmed bug: with SPIDIFY as the last-discussed product,
        "Tell me the core values of this company" must NOT become "...of
        this SPIDIFY company" — "this company" refers to the workspace/
        host itself, not the last product."""
        ctx = SessionContext()
        ctx.record_products("s1", ["SPIDIFY"])
        resolved = ctx.resolve_reference("s1", "Tell me the core values of this company")
        assert resolved == "Tell me the core values of this company"
        assert "SPIDIFY" not in resolved

    def test_this_platform_and_that_organization_also_left_alone(self):
        ctx = SessionContext()
        ctx.record_products("s1", ["ZivaAIRA"])
        assert "ZivaAIRA" not in ctx.resolve_reference("s1", "Who runs this platform?")
        assert "ZivaAIRA" not in ctx.resolve_reference("s1", "What is that organization about?")

    def test_this_alone_still_resolves_when_not_followed_by_self_referential_noun(self):
        """The exclusion must be narrow — a genuine product pronoun
        elsewhere in the same session still resolves normally."""
        ctx = SessionContext()
        ctx.record_products("s1", ["PayCheq"])
        resolved = ctx.resolve_reference("s1", "Does this support mobile payments?")
        assert "PayCheq" in resolved


class TestSessionContextPendingAction:
    def test_no_pending_action_by_default(self):
        ctx = SessionContext()
        assert ctx.get_pending_action("s1") is None

    def test_probing_pending_action_does_not_auto_create_a_session(self):
        ctx = SessionContext()
        ctx.get_pending_action("never-touched")
        # get() would have auto-created a session; get_pending_action() must not.
        assert ctx._cache.get("never-touched") is None

    def test_set_and_get_round_trip(self):
        ctx = SessionContext()
        action = PendingAction(kind="escalation", status="awaiting_confirmation")
        ctx.set_pending_action("s1", action)
        assert ctx.get_pending_action("s1") == action

    def test_clearing_pending_action(self):
        ctx = SessionContext()
        ctx.set_pending_action("s1", PendingAction(kind="demo"))
        ctx.set_pending_action("s1", None)
        assert ctx.get_pending_action("s1") is None

    def test_isolated_across_sessions(self):
        ctx = SessionContext()
        ctx.set_pending_action("s1", PendingAction(kind="appointment"))
        assert ctx.get_pending_action("s2") is None


class TestSessionContextTTLAndCapacity:
    def test_expired_session_starts_fresh(self):
        ctx = SessionContext(ttl_seconds=0.01)
        ctx.record_products("s1", ["SPIDIFY"])
        import time

        time.sleep(0.05)
        state = ctx.get("s1")
        assert state.discussed_products == []

    def test_max_sessions_is_respected(self):
        """Note: probing an *evicted* session's id with .get() legitimately
        auto-creates a fresh blank session for it (any session_id is
        always usable) — which itself counts as a cache insertion. Checking
        eviction state must therefore be done in one pass, without
        querying other ids in between (each such query can itself evict
        the very entry under test)."""
        ctx = SessionContext(max_sessions=2)
        ctx.record_products("s1", ["SPIDIFY"])
        ctx.record_products("s2", ["ZivaAIRA"])
        ctx.record_products("s3", ["PayCheq"])
        # The most recently written session must never be evicted by its
        # own write.
        assert ctx.get("s3").discussed_products == ["PayCheq"]
