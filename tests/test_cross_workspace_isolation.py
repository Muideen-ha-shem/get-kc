"""Cross-tenant isolation checks (Phase 22) — a workspace-A-scoped request
must never surface workspace-B rows. All Supabase calls mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.conversation.conversation_repository import ConversationRepository
from src.services.saved_items.saved_comparison_service import SavedComparisonService


class TestKnowledgeRetrievalIsolation:
    def test_workspace_a_request_only_ever_queries_workspace_a(self):
        """The RPC call itself carries workspace A's id — the DB, not the
        app, is what excludes workspace B's rows, but this pins that the
        app always sends the *right* id rather than trusting the prompt."""
        from src.api.services import retrieval

        mock_sb_client = MagicMock()
        response = MagicMock()
        response.data = [{"parent_url": "https://a.example.com", "chunk_content": "workspace A content", "similarity": 0.9}]
        mock_sb_client.rpc.return_value.execute.return_value = response

        with patch.object(retrieval, "get_client", return_value=mock_sb_client), \
             patch.object(retrieval, "embed_query", return_value=[0.1]):
            matches, _, _ = retrieval.retrieve_context("question", workspace_id="workspace-a")

        rpc_name, rpc_params = mock_sb_client.rpc.call_args.args
        assert rpc_name == "match_documents_by_workspace"
        assert rpc_params["workspace_id"] == "workspace-a"
        assert rpc_params["workspace_id"] != "workspace-b"
        assert matches[0]["chunk_content"] == "workspace A content"


class TestConversationIsolation:
    def test_list_conversations_scopes_query_to_requested_workspace(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": "c1", "user_id": "u1", "title": "t", "created_at": None, "updated_at": None, "workspace_id": "workspace-a"}
        ]
        repo = ConversationRepository(client=client)

        repo.list_conversations("u1", workspace_id="workspace-a")

        client.table.return_value.select.return_value.eq.return_value.eq.assert_called_once_with(
            "workspace_id", "workspace-a"
        )

    def test_list_conversations_without_workspace_id_does_not_filter(self):
        """Backward compat: an unscoped call (no workspace_id) must not add
        a workspace filter at all — see test_conversation_service.py's
        pre-existing assertions for the exact unfiltered chain shape."""
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        repo = ConversationRepository(client=client)

        repo.list_conversations("u1")

        client.table.return_value.select.return_value.eq.return_value.eq.assert_not_called()


class TestSavedComparisonIsolation:
    def test_save_writes_the_resolved_workspace_id_not_the_default(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "cmp1", "user_id": "u1", "product_ids": ["SPIDIFY"], "created_at": None}
        ]
        service = SavedComparisonService(client=client)

        service.save("u1", ["SPIDIFY"], workspace_id="workspace-b")

        payload = client.table.return_value.insert.call_args[0][0]
        assert payload["workspace_id"] == "workspace-b"

    def test_list_for_user_scopes_to_requested_workspace(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        service = SavedComparisonService(client=client)

        service.list_for_user("u1", workspace_id="workspace-b")

        client.table.return_value.select.return_value.eq.return_value.eq.assert_called_once_with(
            "workspace_id", "workspace-b"
        )
