"""Tests for src/api/services/retrieval.py — retrieve_context()'s product_filter plumbing.

All Supabase/embedding calls are mocked — no network access.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _mock_rpc_response(data):
    response = MagicMock()
    response.data = data
    return response


class TestRetrieveContextDefaultPath:
    def test_no_product_filter_calls_match_documents(self):
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

    def test_empty_product_filter_list_calls_match_documents(self):
        """An empty list is falsy — must behave exactly like None, not send an empty filter."""
        from src.api.services import retrieval

        mock_sb_client = MagicMock()
        mock_sb_client.rpc.return_value.execute.return_value = _mock_rpc_response([])

        with patch.object(retrieval, "get_client", return_value=mock_sb_client), \
             patch.object(retrieval, "embed_query", return_value=[0.1, 0.2]):
            retrieval.retrieve_context("test question", product_filter=[])

        mock_sb_client.rpc.assert_called_once_with(
            "match_documents",
            {"query_embedding": [0.1, 0.2], "match_threshold": 0.2, "match_count": 3},
        )


class TestRetrieveContextProductFilter:
    def test_product_filter_calls_match_documents_by_product(self):
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

    def test_multiple_products_in_filter(self):
        from src.api.services import retrieval

        mock_sb_client = MagicMock()
        mock_sb_client.rpc.return_value.execute.return_value = _mock_rpc_response([])

        with patch.object(retrieval, "get_client", return_value=mock_sb_client), \
             patch.object(retrieval, "embed_query", return_value=[0.1, 0.2]):
            retrieval.retrieve_context("test question", product_filter=["SPIDIFY", "ZivaAIRA"])

        call_args = mock_sb_client.rpc.call_args
        assert call_args.args[0] == "match_documents_by_product"
        assert call_args.args[1]["product_filter"] == ["SPIDIFY", "ZivaAIRA"]


class TestRetrieveContextReturnShape:
    def test_none_data_returns_empty_results(self):
        from src.api.services import retrieval

        mock_sb_client = MagicMock()
        mock_sb_client.rpc.return_value.execute.return_value = _mock_rpc_response(None)

        with patch.object(retrieval, "get_client", return_value=mock_sb_client), \
             patch.object(retrieval, "embed_query", return_value=[0.1]):
            matches, similarities, urls = retrieval.retrieve_context("test")

        assert matches == []
        assert similarities == []
        assert urls == []

    def test_matches_similarities_and_urls_extracted(self):
        from src.api.services import retrieval

        data = [
            {"parent_url": "https://a.example.com", "chunk_content": "A", "similarity": 0.9},
            {"parent_url": "https://b.example.com", "chunk_content": "B", "similarity": 0.7},
        ]
        mock_sb_client = MagicMock()
        mock_sb_client.rpc.return_value.execute.return_value = _mock_rpc_response(data)

        with patch.object(retrieval, "get_client", return_value=mock_sb_client), \
             patch.object(retrieval, "embed_query", return_value=[0.1]):
            matches, similarities, urls = retrieval.retrieve_context("test")

        assert matches == data
        assert similarities == [0.9, 0.7]
        assert urls == ["https://a.example.com", "https://b.example.com"]
