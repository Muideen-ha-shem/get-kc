"""Tests for src/api/services/retrieval.py's workspace_id plumbing (Phase 22).

All Supabase/embedding calls are mocked — no network access. Companion to
test_retrieval.py, which pins the pre-Phase-22 (workspace_id=None) branches
unchanged.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _mock_rpc_response(data):
    response = MagicMock()
    response.data = data
    return response


class TestRetrieveContextWorkspaceScoped:
    def test_workspace_id_calls_match_documents_by_workspace(self):
        from src.api.services import retrieval

        mock_sb_client = MagicMock()
        mock_sb_client.rpc.return_value.execute.return_value = _mock_rpc_response([])

        with patch.object(retrieval, "get_client", return_value=mock_sb_client), \
             patch.object(retrieval, "embed_query", return_value=[0.1, 0.2]):
            retrieval.retrieve_context("test question", workspace_id="ws-1")

        mock_sb_client.rpc.assert_called_once_with(
            "match_documents_by_workspace",
            {
                "query_embedding": [0.1, 0.2],
                "match_threshold": 0.2,
                "match_count": 3,
                "workspace_id": "ws-1",
                "product_filter": None,
            },
        )

    def test_workspace_id_with_product_filter_combines_both(self):
        from src.api.services import retrieval

        mock_sb_client = MagicMock()
        mock_sb_client.rpc.return_value.execute.return_value = _mock_rpc_response([])

        with patch.object(retrieval, "get_client", return_value=mock_sb_client), \
             patch.object(retrieval, "embed_query", return_value=[0.1, 0.2]):
            retrieval.retrieve_context("test question", product_filter=["SPIDIFY"], workspace_id="ws-1")

        mock_sb_client.rpc.assert_called_once_with(
            "match_documents_by_workspace",
            {
                "query_embedding": [0.1, 0.2],
                "match_threshold": 0.2,
                "match_count": 3,
                "workspace_id": "ws-1",
                "product_filter": ["SPIDIFY"],
            },
        )

    def test_no_workspace_id_still_calls_match_documents(self):
        """Regression pin: omitting workspace_id must hit the exact
        pre-Phase-22 branch, not the new workspace-scoped RPC."""
        from src.api.services import retrieval

        mock_sb_client = MagicMock()
        mock_sb_client.rpc.return_value.execute.return_value = _mock_rpc_response([])

        with patch.object(retrieval, "get_client", return_value=mock_sb_client), \
             patch.object(retrieval, "embed_query", return_value=[0.1, 0.2]):
            retrieval.retrieve_context("test question")

        mock_sb_client.rpc.assert_called_once_with(
            "match_documents",
            {"query_embedding": [0.1, 0.2], "match_threshold": 0.2, "match_count": 3},
        )

    def test_no_workspace_id_with_product_filter_still_calls_match_documents_by_product(self):
        from src.api.services import retrieval

        mock_sb_client = MagicMock()
        mock_sb_client.rpc.return_value.execute.return_value = _mock_rpc_response([])

        with patch.object(retrieval, "get_client", return_value=mock_sb_client), \
             patch.object(retrieval, "embed_query", return_value=[0.1, 0.2]):
            retrieval.retrieve_context("test question", product_filter=["SPIDIFY"])

        mock_sb_client.rpc.assert_called_once_with(
            "match_documents_by_product",
            {
                "query_embedding": [0.1, 0.2],
                "match_threshold": 0.2,
                "match_count": 3,
                "product_filter": ["SPIDIFY"],
            },
        )
