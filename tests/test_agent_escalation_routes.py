"""Integration tests for the Phase 24 agent/escalation routes — mirrors
test_chat_workspace_routes.py's dependency_overrides + patched-singleton
pattern.

Agent-identity routes (/agents/me, /agents/status, /agent/*) resolve via
get_current_agent (identity-based — see deps.py's docstring for why this
replaced get_current_workspace for these routes), so tests override that
dependency directly rather than get_current_workspace. /chat/escalate
stays on get_current_workspace since it's a customer-facing route.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.deps import (
    get_current_access_token,
    get_current_agent,
    get_current_chat_workspace,
    get_current_user_optional,
    get_current_user_required,
    get_current_workspace,
)
from src.services.agents.agent_models import SupportAgent
from src.services.auth.auth_service import AuthUser
from src.services.escalation.escalation_models import Escalation
from src.services.workspace.workspace_context import WorkspaceContext

_FAKE_USER = AuthUser(id="u1", email="ada@example.com", full_name="Ada")
_FAKE_WORKSPACE = WorkspaceContext(workspace_id="w1", slug="acme", name="Acme")


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _agent(**overrides) -> SupportAgent:
    base = {
        "id": "a1", "workspace_id": "w1", "auth_user_id": "u1", "name": "Ada",
        "email": "ada@example.com", "department": "General", "status": "offline",
        "created_at": None, "updated_at": None,
    }
    base.update(overrides)
    return SupportAgent(**base)


def _authenticate():
    """For customer-facing routes still on get_current_workspace (/chat/escalate)."""
    app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
    app.dependency_overrides[get_current_user_optional] = lambda: _FAKE_USER
    app.dependency_overrides[get_current_workspace] = lambda: _FAKE_WORKSPACE


def _authenticate_chat_workspace():
    """For the new customer-facing routes on get_current_chat_workspace
    (GET /chat/escalations/{id}, GET /chat/conversations/{id}/escalation)."""
    app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
    app.dependency_overrides[get_current_chat_workspace] = lambda: _FAKE_WORKSPACE
    app.dependency_overrides[get_current_access_token] = lambda: "token-1"


def _authenticate_as_agent(agent: SupportAgent | None = None):
    """For identity-based agent routes (/agents/me, /agents/status, /agent/*)."""
    app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
    app.dependency_overrides[get_current_user_optional] = lambda: _FAKE_USER
    app.dependency_overrides[get_current_agent] = lambda: agent or _agent()


def _escalation(**overrides) -> Escalation:
    base = {
        "id": "e1", "workspace_id": "w1", "conversation_id": None, "status": "waiting",
        "assigned_agent_id": None, "trigger_reason": "explicit_request", "department": None,
        "summary": {"customer": "Unknown", "workspace": "Acme", "intent": [], "sentiment": "neutral",
                     "products": [], "problem": "help", "actions_already_taken": [], "suggested_resolution": []},
        "created_at": None, "assigned_at": None, "resolved_at": None, "closed_at": None,
    }
    base.update(overrides)
    return Escalation(**base)


class TestAgentsRoutes:
    def test_agents_me_returns_existing_agent(self, client):
        _authenticate_as_agent(_agent())
        response = client.get("/agents/me")

        assert response.status_code == 200
        assert response.json()["id"] == "a1"

    def test_agents_me_404s_when_not_registered(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        with patch(
            "src.api.deps._agent_service.get_by_auth_user_id_any_workspace", return_value=None
        ):
            response = client.get("/agents/me")

        assert response.status_code == 404

    def test_update_status_returns_404_when_not_an_agent(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        with patch(
            "src.api.deps._agent_service.get_by_auth_user_id_any_workspace", return_value=None
        ):
            response = client.patch("/agents/status", json={"status": "available"})

        assert response.status_code == 404

    def test_update_status_updates_when_registered(self, client):
        _authenticate_as_agent(_agent())
        with patch("src.api.routes.agents._agent_service.update_status", return_value=_agent(status="available")):
            response = client.patch("/agents/status", json={"status": "available"})

        assert response.status_code == 200
        assert response.json()["status"] == "available"

    def test_get_targets_returns_configured_workspace_targets(self, client):
        from types import SimpleNamespace

        _authenticate_as_agent(_agent())
        settings = SimpleNamespace(
            target_resolution_rate=0.9, target_response_minutes=5.0,
            target_resolution_minutes=30.0, target_csat=None,
        )
        with patch("src.api.routes.agents._settings_service.get", return_value=settings) as mock_get:
            response = client.get("/agents/targets")

        assert response.status_code == 200
        body = response.json()
        assert body["resolution_rate"] == 0.9
        assert body["response_minutes"] == 5.0
        assert body["resolution_minutes"] == 30.0
        assert body["csat"] is None
        mock_get.assert_called_once_with("w1")


class TestEscalationRoutes:
    def test_chat_escalate_creates_and_notifies(self, client):
        _authenticate()
        with patch(
            "src.api.routes.escalation._escalation_service.create_direct", return_value=_escalation()
        ) as mock_create:
            response = client.post("/chat/escalate", json={"question": "talk to a human", "conversation_id": None})

        assert response.status_code == 200
        assert response.json()["id"] == "e1"
        mock_create.assert_called_once()

    def test_agent_queue_requires_registered_agent(self, client):
        app.dependency_overrides[get_current_user_required] = lambda: _FAKE_USER
        with patch(
            "src.api.deps._agent_service.get_by_auth_user_id_any_workspace", return_value=None
        ):
            response = client.get("/agent/queue")

        assert response.status_code == 404

    def test_agent_queue_scoped_to_workspace(self, client):
        _authenticate_as_agent(_agent())
        with patch(
            "src.api.routes.escalation._escalation_repository.list_waiting", return_value=[_escalation()]
        ) as mock_list:
            response = client.get("/agent/queue")

        assert response.status_code == 200
        assert len(response.json()) == 1
        mock_list.assert_called_once_with("w1")

    def test_accept_already_assigned_returns_409(self, client):
        _authenticate_as_agent(_agent())
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="assigned"),
        ):
            response = client.post("/agent/accept", json={"escalation_id": "e1"})

        assert response.status_code == 409

    def test_accept_waiting_escalation_succeeds(self, client):
        _authenticate_as_agent(_agent(status="available"))
        with patch("src.api.routes.escalation._escalation_repository.get", return_value=_escalation()), \
             patch(
                 "src.api.routes.escalation._escalation_repository.assign",
                 return_value=_escalation(status="assigned", assigned_agent_id="a1"),
             ) as mock_assign:
            response = client.post("/agent/accept", json={"escalation_id": "e1"})

        assert response.status_code == 200
        assert response.json()["status"] == "assigned"
        mock_assign.assert_called_once_with("e1", "a1")

    def test_accept_rejected_when_agent_not_available(self, client):
        _authenticate_as_agent(_agent(status="away"))
        response = client.post("/agent/accept", json={"escalation_id": "e1"})

        assert response.status_code == 409

    def test_copilot_suggest_reply_passes_conversation_transcript(self, client):
        _authenticate_as_agent(_agent())
        escalation = _escalation()
        with patch("src.api.routes.escalation._escalation_repository.get", return_value=escalation), \
             patch(
                 "src.api.routes.escalation._escalation_repository.list_messages",
                 return_value=[
                     MagicMock(sender_type="customer", content="I need help"),
                     MagicMock(sender_type="agent", content="Sure, what's up?"),
                 ],
             ), \
             patch(
                 "src.api.routes.escalation.suggest_reply",
                 return_value={"draft": "Summary of the chat.", "citations": []},
             ) as mock_suggest:
            response = client.post(
                f"/agent/escalations/{escalation.id}/copilot/suggest-reply",
                json={"question": "Summarize this conversation"},
            )

        assert response.status_code == 200
        assert response.json()["draft"] == "Summary of the chat."
        _, kwargs = mock_suggest.call_args
        assert "Customer: I need help" in kwargs["conversation_transcript"]
        assert "Agent: Sure, what's up?" in kwargs["conversation_transcript"]

    def test_resolve_requires_assigned_or_active(self, client):
        _authenticate_as_agent(_agent())
        with patch("src.api.routes.escalation._escalation_repository.get", return_value=_escalation(status="waiting")):
            response = client.post("/agent/resolve", json={"escalation_id": "e1"})

        assert response.status_code == 409

    def test_resolve_succeeds_when_active(self, client):
        _authenticate_as_agent(_agent())
        with patch("src.api.routes.escalation._escalation_repository.get", return_value=_escalation(status="active")), \
             patch(
                 "src.api.routes.escalation._escalation_repository.mark_resolved",
                 return_value=_escalation(status="resolved"),
             ), \
             patch(
                 "src.api.routes.escalation._escalation_service.generate_resolution_summary", return_value=None,
             ):
            response = client.post("/agent/resolve", json={"escalation_id": "e1"})

        assert response.status_code == 200
        assert response.json()["status"] == "resolved"

    def test_resolve_drafts_a_summary_and_merges_it_into_the_response(self, client):
        _authenticate_as_agent(_agent())
        resolved_with_summary = _escalation(
            status="resolved",
            summary={**_escalation().summary, "resolution": "Customer's issue was resolved."},
        )
        with patch("src.api.routes.escalation._escalation_repository.get", return_value=_escalation(status="active")), \
             patch(
                 "src.api.routes.escalation._escalation_repository.mark_resolved",
                 return_value=_escalation(status="resolved"),
             ), \
             patch(
                 "src.api.routes.escalation._escalation_service.generate_resolution_summary",
                 return_value="Customer's issue was resolved.",
             ), \
             patch(
                 "src.api.routes.escalation._escalation_repository.merge_summary",
                 return_value=resolved_with_summary,
             ) as mock_merge:
            response = client.post("/agent/resolve", json={"escalation_id": "e1"})

        assert response.status_code == 200
        mock_merge.assert_called_once_with("e1", {"resolution": "Customer's issue was resolved."})
        assert response.json()["summary"]["resolution"] == "Customer's issue was resolved."

    def test_close_requires_resolved_status(self, client):
        _authenticate_as_agent(_agent())
        with patch("src.api.routes.escalation._escalation_repository.get", return_value=_escalation(status="active")):
            response = client.post("/agent/escalations/e1/close", json={})

        assert response.status_code == 409

    def test_close_succeeds_and_calls_mark_closed(self, client):
        """The first-ever exercise of mark_closed() through a real route —
        previously dead code with no caller anywhere."""
        _authenticate_as_agent(_agent())
        with patch(
            "src.api.routes.escalation._escalation_repository.get", return_value=_escalation(status="resolved"),
        ), patch(
            "src.api.routes.escalation._escalation_repository.mark_closed",
            return_value=_escalation(status="closed", closed_at="2026-01-01T00:00:00Z"),
        ) as mock_mark_closed:
            response = client.post("/agent/escalations/e1/close", json={})

        assert response.status_code == 200
        assert response.json()["status"] == "closed"
        mock_mark_closed.assert_called_once_with("e1")

    def test_close_with_edited_summary_persists_it_before_closing(self, client):
        _authenticate_as_agent(_agent())
        with patch(
            "src.api.routes.escalation._escalation_repository.get", return_value=_escalation(status="resolved"),
        ), patch(
            "src.api.routes.escalation._escalation_repository.merge_summary",
        ) as mock_merge, patch(
            "src.api.routes.escalation._escalation_repository.mark_closed",
            return_value=_escalation(status="closed"),
        ):
            response = client.post(
                "/agent/escalations/e1/close", json={"resolution_summary": "Agent-edited final summary."}
            )

        assert response.status_code == 200
        mock_merge.assert_called_once_with("e1", {"resolution": "Agent-edited final summary."})

    def test_message_transitions_to_active_on_first_message(self, client):
        _authenticate()
        message_row = MagicMock(
            id="m1", sender_type="agent", sender_auth_user_id="u1", content="hi", created_at=None
        )
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="assigned", assigned_agent_id="a1"),
        ), patch(
            "src.api.routes.escalation._agent_service.get_by_auth_user_id_any_workspace", return_value=_agent()
        ), patch(
               "src.api.routes.escalation._escalation_repository.mark_active_if_first_message"
           ) as mock_mark_active, \
           patch(
               "src.api.routes.escalation._escalation_repository.add_message", return_value=message_row
           ) as mock_add:
            response = client.post("/agent/escalations/e1/messages", json={"content": "hi"})

        assert response.status_code == 200
        mock_mark_active.assert_called_once_with("e1")
        mock_add.assert_called_once_with("e1", "agent", "u1", "hi")

    def test_message_customer_ownership_check_passes(self, client):
        _authenticate()
        app.dependency_overrides[get_current_access_token] = lambda: "token-1"
        message_row = MagicMock(
            id="m1", sender_type="customer", sender_auth_user_id="u1", content="hi", created_at=None
        )
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="assigned", assigned_agent_id="a1", conversation_id="c1"),
        ), patch(
            "src.api.routes.escalation._agent_service.get_by_auth_user_id_any_workspace", return_value=None
        ), patch(
            "src.api.routes.escalation._conversation_service.get_conversation", return_value=MagicMock()
        ), patch(
            "src.api.routes.escalation._escalation_repository.mark_active_if_first_message"
        ), patch(
            "src.api.routes.escalation._escalation_repository.set_active"
        ), patch(
            "src.api.routes.escalation._escalation_repository.add_message", return_value=message_row
        ):
            response = client.post("/agent/escalations/e1/messages", json={"content": "hi"})

        assert response.status_code == 200

    def test_message_customer_ownership_check_blocks_non_owner(self, client):
        _authenticate()
        app.dependency_overrides[get_current_access_token] = lambda: "token-1"
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="assigned", assigned_agent_id="a1", conversation_id="c1"),
        ), patch(
            "src.api.routes.escalation._agent_service.get_by_auth_user_id_any_workspace", return_value=None
        ), patch(
            "src.api.routes.escalation._conversation_service.get_conversation", return_value=None
        ) as mock_get_conversation:
            response = client.post("/agent/escalations/e1/messages", json={"content": "hi"})

        assert response.status_code == 404
        mock_get_conversation.assert_called_once()

    def test_message_customer_blocked_when_escalation_has_no_conversation_id(self, client):
        _authenticate()
        app.dependency_overrides[get_current_access_token] = lambda: "token-1"
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="waiting", conversation_id=None),
        ), patch(
            "src.api.routes.escalation._agent_service.get_by_auth_user_id_any_workspace", return_value=None
        ), patch(
            "src.api.routes.escalation._conversation_service.get_conversation"
        ) as mock_get_conversation:
            response = client.post("/agent/escalations/e1/messages", json={"content": "hi"})

        assert response.status_code == 404
        mock_get_conversation.assert_not_called()

    def test_message_agent_branch_never_calls_ownership_check(self, client):
        _authenticate()
        message_row = MagicMock(
            id="m1", sender_type="agent", sender_auth_user_id="u1", content="hi", created_at=None
        )
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="assigned", assigned_agent_id="a1"),
        ), patch(
            "src.api.routes.escalation._agent_service.get_by_auth_user_id_any_workspace", return_value=_agent()
        ), patch(
            "src.api.routes.escalation._conversation_service.get_conversation"
        ) as mock_get_conversation, patch(
            "src.api.routes.escalation._escalation_repository.mark_active_if_first_message"
        ), patch(
            "src.api.routes.escalation._escalation_repository.add_message", return_value=message_row
        ):
            response = client.post("/agent/escalations/e1/messages", json={"content": "hi"})

        assert response.status_code == 200
        mock_get_conversation.assert_not_called()

    def test_message_rejected_for_non_assigned_agent(self, client):
        """Live-confirmed gap: a different agent in the same workspace
        posting to someone else's escalation used to be silently
        relabeled sender_type="customer" instead of rejected."""
        _authenticate()
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="assigned", assigned_agent_id="a1"),
        ), patch(
            "src.api.routes.escalation._agent_service.get_by_auth_user_id_any_workspace",
            return_value=_agent(id="a2"),
        ), patch(
            "src.api.routes.escalation._escalation_repository.add_message"
        ) as mock_add_message:
            response = client.post("/agent/escalations/e1/messages", json={"content": "hi"})

        assert response.status_code == 403
        mock_add_message.assert_not_called()

    def test_message_rejected_for_agent_posting_to_unclaimed_escalation(self, client):
        _authenticate()
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="waiting", assigned_agent_id=None),
        ), patch(
            "src.api.routes.escalation._agent_service.get_by_auth_user_id_any_workspace", return_value=_agent()
        ), patch(
            "src.api.routes.escalation._escalation_repository.add_message"
        ) as mock_add_message:
            response = client.post("/agent/escalations/e1/messages", json={"content": "hi"})

        assert response.status_code == 403
        mock_add_message.assert_not_called()


class TestRejoinAi:
    def test_handoff_recap_is_persisted_not_just_returned(self, client):
        """Live-confirmed gap: rejoin-ai built a handoff_recap and returned
        it to the AGENT's own browser session, but never persisted it —
        the customer (a different browser session entirely) had no way to
        ever see it."""
        _authenticate_as_agent(_agent())
        resolved = _escalation(status="resolved")
        with patch(
            "src.api.routes.escalation._escalation_repository.get", return_value=_escalation(status="active"),
        ), patch(
            "src.api.routes.escalation._escalation_repository.list_messages", return_value=[],
        ), patch(
            "src.api.routes.escalation._escalation_repository.list_notes", return_value=[],
        ), patch(
            "src.api.routes.escalation._escalation_repository.mark_resolved", return_value=resolved,
        ), patch(
            "src.api.routes.escalation._escalation_repository.set_ai_engaged", return_value=resolved,
        ), patch(
            "src.api.routes.escalation._escalation_repository.merge_summary", return_value=resolved,
        ) as mock_merge:
            response = client.post("/agent/escalations/e1/rejoin-ai")

        assert response.status_code == 200
        assert "handoff_recap" in response.json()
        assert mock_merge.call_args[0][0] == "e1"
        assert "handoff_recap" in mock_merge.call_args[0][1]


class TestCustomerEscalationRoutes:
    def test_get_escalation_happy_path_omits_notes_and_summary(self, client):
        _authenticate_chat_workspace()
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="active", assigned_agent_id="a1", conversation_id="c1"),
        ), patch(
            "src.api.routes.escalation._conversation_service.get_conversation", return_value=MagicMock()
        ), patch(
            "src.api.routes.escalation._escalation_repository.list_messages", return_value=[]
        ), patch(
            "src.api.routes.escalation._agent_service.get_by_id", return_value=_agent(name="Ada")
        ):
            response = client.get("/chat/escalations/e1")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "e1"
        assert body["assigned_agent_name"] == "Ada"
        assert "notes" not in body
        assert "summary" not in body

    def test_get_escalation_surfaces_handoff_recap_to_the_customer(self, client):
        """The one deliberate exception to CustomerEscalationSchema's
        "never expose internal summary" rule — see the schema's own field
        docstring. Confirms the fix: the customer's own poll of their
        escalation is how they'd actually receive a rejoin-ai recap."""
        _authenticate_chat_workspace()
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(
                status="resolved", assigned_agent_id="a1", conversation_id="c1",
                summary={**_escalation().summary, "handoff_recap": "Customer needed help with V-Login access."},
            ),
        ), patch(
            "src.api.routes.escalation._conversation_service.get_conversation", return_value=MagicMock()
        ), patch(
            "src.api.routes.escalation._escalation_repository.list_messages", return_value=[]
        ), patch(
            "src.api.routes.escalation._agent_service.get_by_id", return_value=_agent(name="Ada")
        ):
            response = client.get("/chat/escalations/e1")

        assert response.status_code == 200
        assert response.json()["handoff_recap"] == "Customer needed help with V-Login access."

    def test_get_escalation_blocked_for_non_owner(self, client):
        _authenticate_chat_workspace()
        with patch(
            "src.api.routes.escalation._escalation_repository.get",
            return_value=_escalation(status="active", conversation_id="c1"),
        ), patch(
            "src.api.routes.escalation._conversation_service.get_conversation", return_value=None
        ):
            response = client.get("/chat/escalations/e1")

        assert response.status_code == 404

    def test_lookup_by_conversation_found(self, client):
        _authenticate_chat_workspace()
        with patch(
            "src.api.routes.escalation._conversation_service.get_conversation", return_value=MagicMock()
        ), patch(
            "src.api.routes.escalation._escalation_repository.list_by_conversation_ids",
            return_value=[_escalation(status="waiting", conversation_id="c1")],
        ):
            response = client.get("/chat/conversations/c1/escalation")

        assert response.status_code == 200
        assert response.json()["id"] == "e1"

    def test_lookup_by_conversation_none_found_returns_null_body(self, client):
        _authenticate_chat_workspace()
        with patch(
            "src.api.routes.escalation._conversation_service.get_conversation", return_value=MagicMock()
        ), patch(
            "src.api.routes.escalation._escalation_repository.list_by_conversation_ids", return_value=[]
        ):
            response = client.get("/chat/conversations/c1/escalation")

        assert response.status_code == 200
        assert response.json() is None

    def test_lookup_by_conversation_blocked_for_non_owner(self, client):
        _authenticate_chat_workspace()
        with patch(
            "src.api.routes.escalation._conversation_service.get_conversation", return_value=None
        ), patch(
            "src.api.routes.escalation._escalation_repository.list_by_conversation_ids"
        ) as mock_list:
            response = client.get("/chat/conversations/c1/escalation")

        assert response.status_code == 404
        mock_list.assert_not_called()
