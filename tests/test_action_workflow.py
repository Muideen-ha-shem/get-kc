"""Tests for action_workflow — field collection, confirmation summaries, and
the one function (execute_action) that performs a real backend write.

All backend collaborators (escalation_service, appointment_service,
submit_demo_request) are mocked — no real network/DB calls."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.services.advisory.action_workflow import (
    build_confirmation_summary,
    build_field_prompt,
    collect_field,
    execute_action,
    required_fields,
)
from src.services.advisory.session_context import PendingAction, SessionState


# ---------------------------------------------------------------------------
# required_fields
# ---------------------------------------------------------------------------


class TestRequiredFields:
    def test_escalation_needs_nothing(self):
        assert required_fields("escalation", None) == []

    def test_appointment_needs_slot_name_email(self):
        assert required_fields("appointment", None) == ["slot", "name", "email"]

    def test_demo_needs_product_when_unknown(self):
        assert required_fields("demo", None) == ["product", "name", "email", "company"]

    def test_demo_skips_product_when_already_known(self):
        state = SessionState(discussed_products=["SPIDIFY"])
        assert required_fields("demo", state) == ["name", "email", "company"]


# ---------------------------------------------------------------------------
# Field prompts
# ---------------------------------------------------------------------------


class TestBuildFieldPrompt:
    def test_name_prompt(self):
        pending = PendingAction(kind="demo", missing=["name"])
        assert "name" in build_field_prompt(pending).lower()

    def test_slot_prompt_lists_real_availability(self):
        appointment_service = MagicMock()
        appointment_service.get_availability.return_value = [
            SimpleNamespace(
                date="2026-08-13", day_label="Thu", fully_booked=False,
                slots=[{"time": "09:00", "available": True}],
            ),
        ]
        pending = PendingAction(kind="appointment", missing=["slot"])

        prompt = build_field_prompt(pending, appointment_service=appointment_service, workspace_id="w1")

        assert "Thu 09:00" in prompt
        assert pending.offered_slots == ["Thu 09:00::2026-08-13::09:00"]

    def test_slot_prompt_degrades_when_no_availability(self):
        appointment_service = MagicMock()
        appointment_service.get_availability.return_value = []
        pending = PendingAction(kind="appointment", missing=["slot"])

        prompt = build_field_prompt(pending, appointment_service=appointment_service, workspace_id="w1")

        assert "name" in prompt.lower()
        assert "email" in prompt.lower()


# ---------------------------------------------------------------------------
# collect_field
# ---------------------------------------------------------------------------


class TestCollectFieldEmail:
    def test_valid_email_advances(self):
        pending = PendingAction(kind="demo", missing=["email"])
        updated, response = collect_field(pending, "jane@example.com")
        assert updated.fields["email"] == "jane@example.com"
        assert updated.status == "awaiting_confirmation"  # last field
        assert "would you like" in response.lower()

    def test_invalid_email_reprompts_without_advancing(self):
        pending = PendingAction(kind="demo", missing=["email", "company"])
        updated, response = collect_field(pending, "not-an-email")
        assert "email" not in updated.fields
        assert updated.missing == ["email", "company"]
        assert "valid email" in response.lower()


class TestCollectFieldSlot:
    def test_matching_slot_advances_and_stores_date_time(self):
        pending = PendingAction(
            kind="appointment",
            missing=["slot", "name"],
            offered_slots=["Thu 09:00::2026-08-13::09:00", "Thu 10:30::2026-08-13::10:30"],
        )
        updated, response = collect_field(pending, "Thu 09:00 works for me")
        assert updated.fields["date"] == "2026-08-13"
        assert updated.fields["time"] == "09:00"
        assert updated.missing == ["name"]
        assert "name" in response.lower()

    def test_non_matching_slot_reprompts(self):
        pending = PendingAction(
            kind="appointment",
            missing=["slot"],
            offered_slots=["Thu 09:00::2026-08-13::09:00"],
        )
        updated, response = collect_field(pending, "how about 3pm")
        assert "date" not in updated.fields
        assert "Thu 09:00" in response


class TestCollectFieldProduct:
    def test_recognized_product_advances(self):
        pending = PendingAction(kind="demo", missing=["product", "name"])
        updated, response = collect_field(pending, "I'd like to see SPIDIFY")
        assert updated.fields["product"] == "SPIDIFY"
        assert updated.missing == ["name"]

    def test_unrecognized_product_reprompts(self):
        pending = PendingAction(kind="demo", missing=["product"])
        updated, response = collect_field(pending, "the thing you showed me")
        assert "product" not in updated.fields
        assert "which havisiq" in response.lower()


class TestCollectFieldOptional:
    def test_skip_word_accepted_for_company(self):
        pending = PendingAction(kind="demo", missing=["company"], fields={"name": "Jane", "email": "j@x.com"})
        updated, response = collect_field(pending, "skip")
        assert updated.fields["company"] == ""
        assert updated.status == "awaiting_confirmation"

    def test_real_company_name_accepted(self):
        pending = PendingAction(kind="demo", missing=["company"], fields={"name": "Jane", "email": "j@x.com"})
        updated, response = collect_field(pending, "Acme Ltd")
        assert updated.fields["company"] == "Acme Ltd"


class TestCollectFieldName:
    def test_blank_reprompts(self):
        pending = PendingAction(kind="demo", missing=["name", "email"])
        updated, response = collect_field(pending, "   ")
        assert "name" not in updated.fields
        assert updated.missing == ["name", "email"]


# ---------------------------------------------------------------------------
# build_confirmation_summary
# ---------------------------------------------------------------------------


class TestBuildConfirmationSummary:
    def test_escalation_never_claims_success(self):
        summary = build_confirmation_summary(PendingAction(kind="escalation"))
        for phrase in ("i've connected", "i have connected", "arranged", "booked", "submitted"):
            assert phrase not in summary.lower()
        assert "would you like me to go ahead" in summary.lower()

    def test_appointment_summary_includes_collected_fields(self):
        pending = PendingAction(
            kind="appointment", fields={"slot_label": "Thu 09:00", "name": "Jane", "email": "j@x.com"}
        )
        summary = build_confirmation_summary(pending)
        assert "Thu 09:00" in summary
        assert "Jane" in summary
        assert "j@x.com" in summary

    def test_demo_summary_includes_company_only_when_present(self):
        pending = PendingAction(kind="demo", fields={"product": "SPIDIFY", "name": "Jane", "email": "j@x.com"})
        summary = build_confirmation_summary(pending)
        assert "Company" not in summary

        pending.fields["company"] = "Acme"
        summary = build_confirmation_summary(pending)
        assert "Acme" in summary


# ---------------------------------------------------------------------------
# execute_action
# ---------------------------------------------------------------------------


class TestExecuteActionEscalation:
    def test_success_with_assigned_agent(self):
        escalation_service = MagicMock()
        escalation_service.create_direct.return_value = SimpleNamespace(department="Support", assigned_agent_id="agent-1")
        pending = PendingAction(kind="escalation", original_question="Can I talk to someone?")

        answer = execute_action(
            pending, workspace_id="w1", workspace_name="Ha-Shem", conversation_id="c1",
            escalation_service=escalation_service, appointment_service=None,
        )

        escalation_service.create_direct.assert_called_once_with(
            workspace_id="w1", workspace_name="Ha-Shem", conversation_id="c1",
            question="Can I talk to someone?", trigger_reason="explicit_request",
        )
        assert "support specialist" in answer.lower()
        assert "connected" in answer.lower()

    def test_success_no_agent_available_reports_queue_honestly(self):
        escalation_service = MagicMock()
        escalation_service.create_direct.return_value = SimpleNamespace(department="Sales", assigned_agent_id=None)
        pending = PendingAction(kind="escalation", original_question="Talk to sales")

        answer = execute_action(
            pending, workspace_id="w1", workspace_name="Ha-Shem", conversation_id=None,
            escalation_service=escalation_service, appointment_service=None,
        )

        assert "connected" not in answer.lower()
        assert "queue" in answer.lower()

    def test_no_service_configured_is_honest_not_fabricated(self):
        pending = PendingAction(kind="escalation")
        answer = execute_action(
            pending, workspace_id="w1", workspace_name="Ha-Shem", conversation_id=None,
            escalation_service=None, appointment_service=None,
        )
        assert "wasn't able" in answer.lower()

    def test_backend_exception_reported_honestly_not_raised(self):
        escalation_service = MagicMock()
        escalation_service.create_direct.side_effect = RuntimeError("db down")
        pending = PendingAction(kind="escalation")

        answer = execute_action(
            pending, workspace_id="w1", workspace_name="Ha-Shem", conversation_id=None,
            escalation_service=escalation_service, appointment_service=None,
        )
        assert "wasn't able" in answer.lower()


class TestExecuteActionAppointment:
    def test_success_reports_real_confirmed_slot(self):
        appointment_service = MagicMock()
        appointment_service.book.return_value = SimpleNamespace(appointment_date="2026-08-13", time_slot="09:00")
        pending = PendingAction(kind="appointment", fields={"date": "2026-08-13", "time": "09:00", "name": "Jane", "email": "j@x.com"})

        answer = execute_action(
            pending, workspace_id="w1", workspace_name="Ha-Shem", conversation_id=None,
            escalation_service=None, appointment_service=appointment_service,
        )

        appointment_service.book.assert_called_once_with("2026-08-13", "09:00", "Jane", "j@x.com", workspace_id="w1")
        assert "2026-08-13" in answer
        assert "09:00" in answer
        assert "confirmed" in answer.lower()

    def test_slot_already_booked_reports_honest_failure_with_fresh_availability(self):
        appointment_service = MagicMock()
        appointment_service.book.side_effect = RuntimeError("already booked")
        appointment_service.get_availability.return_value = [
            SimpleNamespace(date="2026-08-14", day_label="Fri", fully_booked=False, slots=[{"time": "10:30", "available": True}]),
        ]
        pending = PendingAction(kind="appointment", fields={"date": "2026-08-13", "time": "09:00", "name": "Jane", "email": "j@x.com"})

        answer = execute_action(
            pending, workspace_id="w1", workspace_name="Ha-Shem", conversation_id=None,
            escalation_service=None, appointment_service=appointment_service,
        )

        assert "confirmed" not in answer.lower()
        assert "Fri 10:30" in answer


class TestExecuteActionDemo:
    def test_success_calls_submit_demo_request_and_reports_honestly(self):
        pending = PendingAction(
            kind="demo",
            fields={"product": "SPIDIFY", "name": "Jane", "email": "j@x.com", "company": "Acme"},
            original_question="I want a demo",
        )

        with patch("src.api.services.demo_requests.submit_demo_request") as mock_submit:
            mock_submit.return_value = {"id": "d1"}
            answer = execute_action(
                pending, workspace_id="w1", workspace_name="Ha-Shem", conversation_id=None,
                escalation_service=None, appointment_service=None,
            )

        mock_submit.assert_called_once_with(
            name="Jane", email="j@x.com", company="Acme", use_case="I want a demo", product="SPIDIFY",
        )
        assert "submitted" in answer.lower()
        assert "SPIDIFY" in answer

    def test_table_missing_reports_honest_failure(self):
        from src.api.services.demo_requests import DemoRequestTableMissingError

        pending = PendingAction(kind="demo", fields={"product": "SPIDIFY", "name": "Jane", "email": "j@x.com"})

        with patch("src.api.services.demo_requests.submit_demo_request", side_effect=DemoRequestTableMissingError("nope")):
            answer = execute_action(
                pending, workspace_id="w1", workspace_name="Ha-Shem", conversation_id=None,
                escalation_service=None, appointment_service=None,
            )

        assert "wasn't able" in answer.lower()
        assert "submitted" not in answer.lower()
